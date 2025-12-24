"""Tests for entity extraction and validation."""

import pytest

from max_os.core.entities import EntityExtractor
from max_os.core.intent import Intent


@pytest.fixture
def entity_extractor():
    return EntityExtractor()


def test_parse_llm_response_valid_json(entity_extractor):
    """Test parsing valid JSON response from LLM."""
    response = """{
  "intent": "file.copy",
  "confidence": 0.95,
  "entities": {
    "source_path": "Documents/report.pdf",
    "dest_path": "Backup"
  },
  "summary": "Copy report.pdf to Backup"
}"""
    
    result = entity_extractor.parse_llm_response(response)
    
    assert result is not None
    assert result["intent"] == "file.copy"
    assert result["confidence"] == 0.95
    assert "source_path" in result["entities"]
    assert result["entities"]["source_path"] == "Documents/report.pdf"


def test_parse_llm_response_with_markdown(entity_extractor):
    """Test parsing JSON wrapped in markdown code blocks."""
    response = """```json
{
  "intent": "system.health",
  "confidence": 0.98,
  "entities": {},
  "summary": "Check system health"
}
```"""
    
    result = entity_extractor.parse_llm_response(response)
    
    assert result is not None
    assert result["intent"] == "system.health"
    assert result["confidence"] == 0.98


def test_parse_llm_response_invalid_json(entity_extractor):
    """Test handling of invalid JSON response."""
    response = "This is not JSON at all"
    
    result = entity_extractor.parse_llm_response(response)
    
    assert result is None


def test_parse_llm_response_missing_confidence(entity_extractor):
    """Test handling of response missing confidence field."""
    response = """{
  "intent": "file.list",
  "entities": {"path": "Documents"}
}"""
    
    result = entity_extractor.parse_llm_response(response)
    
    assert result is not None
    assert result["intent"] == "file.list"
    assert result["confidence"] == 0.5  # Default confidence


def test_extract_intent_from_llm(entity_extractor):
    """Test extracting Intent object from LLM response."""
    response = """{
  "intent": "file.search",
  "confidence": 0.92,
  "entities": {
    "pattern": "*.pdf",
    "size_threshold": "200MB"
  },
  "summary": "Search for PDF files larger than 200MB"
}"""
    
    intent = entity_extractor.extract_intent_from_llm(response)
    
    assert intent is not None
    assert isinstance(intent, Intent)
    assert intent.name == "file.search"
    assert intent.confidence == 0.92
    assert len(intent.slots) == 2
    assert intent.summary == "Search for PDF files larger than 200MB"


def test_normalize_size_bytes(entity_extractor):
    """Test size normalization for bytes."""
    assert entity_extractor.normalize_size("1024") == 1024
    assert entity_extractor.normalize_size("500B") == 500


def test_normalize_size_kilobytes(entity_extractor):
    """Test size normalization for kilobytes."""
    assert entity_extractor.normalize_size("1KB") == 1024
    assert entity_extractor.normalize_size("10K") == 10240


def test_normalize_size_megabytes(entity_extractor):
    """Test size normalization for megabytes."""
    assert entity_extractor.normalize_size("1MB") == 1024 * 1024
    assert entity_extractor.normalize_size("200MB") == 200 * 1024 * 1024


def test_normalize_size_gigabytes(entity_extractor):
    """Test size normalization for gigabytes."""
    assert entity_extractor.normalize_size("1GB") == 1024 * 1024 * 1024
    assert entity_extractor.normalize_size("2GB") == 2 * 1024 * 1024 * 1024


def test_normalize_size_invalid(entity_extractor):
    """Test size normalization for invalid input."""
    assert entity_extractor.normalize_size("invalid") == 0
    assert entity_extractor.normalize_size("") == 0


def test_normalize_path_home_expansion(entity_extractor):
    """Test path normalization with home directory expansion."""
    import os
    
    path = entity_extractor.normalize_path("~/Documents")
    
    # Should expand ~ to home directory
    assert "~" not in path
    assert os.path.expanduser("~") in path


def test_normalize_path_relative(entity_extractor):
    """Test path normalization with relative paths."""
    path = entity_extractor.normalize_path("./Documents")
    
    # Relative paths should be preserved
    assert path == "./Documents"


def test_normalize_path_absolute(entity_extractor):
    """Test path normalization with absolute paths."""
    path = entity_extractor.normalize_path("/home/user/Documents")
    
    assert path == "/home/user/Documents"


def test_validate_path_security_allowed(entity_extractor):
    """Test path security validation for allowed paths."""
    assert entity_extractor.validate_path_security("/home/user/file.txt") is True
    assert entity_extractor.validate_path_security("~/Documents") is True
    assert entity_extractor.validate_path_security("./relative/path") is True


def test_validate_path_security_disallowed(entity_extractor):
    """Test path security validation for disallowed paths."""
    # Paths outside whitelist should be rejected
    assert entity_extractor.validate_path_security("/etc/passwd") is False
    assert entity_extractor.validate_path_security("/root/secret") is False


def test_process_entities_with_paths(entity_extractor):
    """Test entity processing with path normalization."""
    entities = {
        "source_path": "~/Documents/file.pdf",
        "dest_path": "/home/user/Backup"
    }
    
    processed = entity_extractor.process_entities(entities)
    
    assert "source_path" in processed
    assert "dest_path" in processed
    # Tilde should be expanded
    assert "~" not in processed["source_path"]


def test_process_entities_with_size(entity_extractor):
    """Test entity processing with size normalization."""
    entities = {
        "size_threshold": "200MB",
        "pattern": "*.pdf"
    }
    
    processed = entity_extractor.process_entities(entities)
    
    assert processed["size_threshold"] == 200 * 1024 * 1024
    assert processed["pattern"] == "*.pdf"


def test_extract_intent_invalid_response(entity_extractor):
    """Test intent extraction from invalid response."""
    response = "Not a valid JSON response"
    
    intent = entity_extractor.extract_intent_from_llm(response)
    
    assert intent is None


def test_extract_intent_with_empty_entities(entity_extractor):
    """Test intent extraction with no entities."""
    response = """{
  "intent": "system.health",
  "confidence": 0.98,
  "entities": {},
  "summary": "Check system health"
}"""
    
    intent = entity_extractor.extract_intent_from_llm(response)
    
    assert intent is not None
    assert intent.name == "system.health"
    assert len(intent.slots) == 0
