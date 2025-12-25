"""Tests for entity extraction and validation."""

import os

import pytest

from max_os.core.entities import (
    create_intent_from_llm_response,
    extract_and_validate_entities,
    parse_llm_response,
    parse_size_to_bytes,
    validate_file_path,
)
from max_os.core.intent import Intent


class TestParseLLMResponse:
    """Tests for parsing LLM responses."""

    def test_parse_valid_json_response(self):
        """Test parsing a valid JSON response."""
        response = '{"intent": "file.search", "confidence": 0.95, "entities": {"path": "/home"}}'
        result = parse_llm_response(response)

        assert result["intent"] == "file.search"
        assert result["confidence"] == 0.95
        assert result["entities"] == {"path": "/home"}

    def test_parse_json_with_surrounding_text(self):
        """Test parsing JSON embedded in other text."""
        response = 'Sure, here is the classification: {"intent": "file.copy", "confidence": 0.9, "entities": {}}'
        result = parse_llm_response(response)

        assert result["intent"] == "file.copy"
        assert result["confidence"] == 0.9

    def test_parse_missing_confidence(self):
        """Test that missing confidence gets default value."""
        response = '{"intent": "system.health", "entities": {}}'
        result = parse_llm_response(response)

        assert result["intent"] == "system.health"
        assert result["confidence"] == 0.5  # Default

    def test_parse_missing_entities(self):
        """Test that missing entities gets default empty dict."""
        response = '{"intent": "network.ping", "confidence": 0.8}'
        result = parse_llm_response(response)

        assert result["intent"] == "network.ping"
        assert result["entities"] == {}

    def test_parse_missing_intent_raises_error(self):
        """Test that missing intent field raises error."""
        response = '{"confidence": 0.9, "entities": {}}'

        with pytest.raises(ValueError, match="missing 'intent' field"):
            parse_llm_response(response)

    def test_parse_invalid_json_raises_error(self):
        """Test that invalid JSON raises error."""
        response = "not valid json"

        with pytest.raises(ValueError, match="Failed to parse"):
            parse_llm_response(response)


class TestCreateIntentFromLLMResponse:
    """Tests for creating Intent objects from LLM responses."""

    def test_create_intent_with_entities(self):
        """Test creating intent with entities."""
        response = '{"intent": "file.copy", "confidence": 0.92, "entities": {"source_path": "docs/", "dest_path": "backup/"}}'
        intent = create_intent_from_llm_response(response)

        assert isinstance(intent, Intent)
        assert intent.name == "file.copy"
        assert intent.confidence == 0.92
        assert len(intent.slots) == 2
        assert any(s.name == "source_path" and s.value == "docs/" for s in intent.slots)
        assert any(s.name == "dest_path" and s.value == "backup/" for s in intent.slots)

    def test_create_intent_without_entities(self):
        """Test creating intent without entities."""
        response = '{"intent": "system.health", "confidence": 0.98}'
        intent = create_intent_from_llm_response(response)

        assert intent.name == "system.health"
        assert intent.confidence == 0.98
        assert len(intent.slots) == 0

    def test_intent_has_summary(self):
        """Test that created intent has a summary."""
        response = '{"intent": "dev.git_status", "confidence": 0.95}'
        intent = create_intent_from_llm_response(response)

        assert intent.summary is not None
        assert "dev.git_status" in intent.summary


class TestValidateFilePath:
    """Tests for file path validation."""

    def test_expand_home_directory(self):
        """Test that ~ is expanded to home directory."""
        path = "~/Documents"
        result = validate_file_path(path)

        assert "~" not in result
        assert result.startswith(os.path.expanduser("~"))

    def test_convert_relative_to_absolute(self):
        """Test that relative paths are converted to absolute."""
        path = "Documents/file.txt"
        result = validate_file_path(path)

        assert os.path.isabs(result)

    def test_normalize_path(self):
        """Test that paths are normalized."""
        path = "/home/user/../user/Documents"
        result = validate_file_path(path)

        assert ".." not in result
        assert result == os.path.normpath(path)

    def test_whitelist_allows_path(self):
        """Test that whitelisted paths are allowed."""
        path = "/home/user/Documents"
        whitelist = ["/home", "/srv"]

        result = validate_file_path(path, whitelist)
        assert result == path

    def test_whitelist_rejects_path(self):
        """Test that non-whitelisted paths are rejected."""
        path = "/etc/passwd"
        whitelist = ["/home", "/srv"]

        with pytest.raises(ValueError, match="not in allowed directories"):
            validate_file_path(path, whitelist)

    def test_whitelist_with_home_expansion(self):
        """Test whitelist works with ~ expansion."""
        path = "~/Documents"
        home = os.path.expanduser("~")
        whitelist = [home]

        result = validate_file_path(path, whitelist)
        assert result.startswith(home)


class TestParseSizeToBytes:
    """Tests for parsing human-readable sizes to bytes."""

    def test_parse_bytes(self):
        """Test parsing bytes."""
        assert parse_size_to_bytes("100B") == 100
        assert parse_size_to_bytes("100") == 100

    def test_parse_kilobytes(self):
        """Test parsing kilobytes."""
        assert parse_size_to_bytes("1KB") == 1024
        assert parse_size_to_bytes("1K") == 1024
        assert parse_size_to_bytes("2KB") == 2048

    def test_parse_megabytes(self):
        """Test parsing megabytes."""
        assert parse_size_to_bytes("1MB") == 1024**2
        assert parse_size_to_bytes("1M") == 1024**2
        assert parse_size_to_bytes("200MB") == 200 * 1024**2

    def test_parse_gigabytes(self):
        """Test parsing gigabytes."""
        assert parse_size_to_bytes("1GB") == 1024**3
        assert parse_size_to_bytes("1G") == 1024**3
        assert parse_size_to_bytes("1.5GB") == int(1.5 * 1024**3)

    def test_parse_terabytes(self):
        """Test parsing terabytes."""
        assert parse_size_to_bytes("1TB") == 1024**4
        assert parse_size_to_bytes("1T") == 1024**4

    def test_parse_with_spaces(self):
        """Test parsing sizes with spaces."""
        assert parse_size_to_bytes("100 MB") == 100 * 1024**2
        assert parse_size_to_bytes("50 GB") == 50 * 1024**3

    def test_parse_decimal_values(self):
        """Test parsing decimal values."""
        assert parse_size_to_bytes("1.5MB") == int(1.5 * 1024**2)
        assert parse_size_to_bytes("0.5GB") == int(0.5 * 1024**3)

    def test_invalid_format_raises_error(self):
        """Test that invalid formats raise errors."""
        with pytest.raises(ValueError, match="Invalid size format"):
            parse_size_to_bytes("invalid")

        with pytest.raises(ValueError, match="Invalid size format"):
            parse_size_to_bytes("MB100")


class TestExtractAndValidateEntities:
    """Tests for entity extraction and validation."""

    def test_validate_file_paths(self):
        """Test that file paths are validated."""
        entities = {"source_path": "~/Documents/file.txt", "dest_path": "/tmp/backup"}

        result = extract_and_validate_entities(entities)

        assert "~" not in result["source_path"]
        assert os.path.isabs(result["source_path"])
        assert os.path.isabs(result["dest_path"])

    def test_parse_size_thresholds(self):
        """Test that size thresholds are parsed."""
        entities = {"size_threshold": "200MB"}

        result = extract_and_validate_entities(entities)

        assert result["size_threshold"] == "200MB"
        assert result["size_threshold_bytes"] == 200 * 1024**2

    def test_non_path_non_size_entities_unchanged(self):
        """Test that other entities are passed through unchanged."""
        entities = {
            "service_name": "docker.service",
            "host": "google.com",
            "search_query": "kubernetes",
        }

        result = extract_and_validate_entities(entities)

        assert result == entities

    def test_invalid_path_keeps_original(self):
        """Test that invalid paths keep original value."""
        entities = {"source_path": "/etc/passwd"}
        whitelist = ["/home"]

        # Should not raise, but keep original value
        result = extract_and_validate_entities(entities, whitelist)
        assert result["source_path"] == "/etc/passwd"

    def test_invalid_size_keeps_original(self):
        """Test that invalid size strings keep original value."""
        entities = {"size_threshold": "invalid_size"}

        result = extract_and_validate_entities(entities)
        assert result["size_threshold"] == "invalid_size"
        assert "size_threshold_bytes" not in result
