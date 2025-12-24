"""Entity extraction and validation for intent classification."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from max_os.core.intent import Intent, Slot


def parse_llm_response(response_text: str) -> dict[str, Any]:
    """Parse LLM JSON response.

    Args:
        response_text: Raw LLM response text

    Returns:
        Parsed dictionary with intent, confidence, and entities

    Raises:
        ValueError: If response cannot be parsed as JSON
    """
    # Try to extract JSON from response if it contains other text
    response_text = response_text.strip()

    # Look for JSON object in the response (non-greedy match)
    json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group()

    try:
        data = json.loads(response_text)

        # Validate required fields
        if "intent" not in data:
            raise ValueError("Response missing 'intent' field")
        if "confidence" not in data:
            data["confidence"] = 0.5  # Default confidence
        if "entities" not in data:
            data["entities"] = {}

        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {e}") from e


def create_intent_from_llm_response(response_text: str) -> Intent:
    """Create Intent object from LLM response.

    Args:
        response_text: Raw LLM response text

    Returns:
        Intent object with extracted data
    """
    data = parse_llm_response(response_text)

    # Convert entities dict to Slot objects
    slots = [Slot(name=k, value=str(v)) for k, v in data.get("entities", {}).items()]

    return Intent(
        name=data["intent"],
        confidence=float(data.get("confidence", 0.5)),
        slots=slots,
        summary=f"LLM classified as {data['intent']}",
    )


def validate_file_path(path: str, whitelist: list[str] | None = None) -> str:
    """Validate and normalize file path.

    Args:
        path: File path to validate
        whitelist: Optional list of allowed root directories

    Returns:
        Normalized absolute path

    Raises:
        ValueError: If path is invalid or not in whitelist
    """
    # Expand user home directory
    expanded = os.path.expanduser(path)

    # Convert to absolute path if relative
    if not os.path.isabs(expanded):
        expanded = os.path.abspath(expanded)

    # Normalize the path (resolve .., ., etc.)
    normalized = os.path.normpath(expanded)

    # Check whitelist if provided
    if whitelist:
        allowed = False
        for allowed_root in whitelist:
            allowed_root_expanded = os.path.expanduser(allowed_root)
            if normalized.startswith(allowed_root_expanded):
                allowed = True
                break

        if not allowed:
            raise ValueError(f"Path {normalized} is not in allowed directories: {whitelist}")

    return normalized


def parse_size_to_bytes(size_str: str) -> int:
    """Convert human-readable size to bytes.

    Args:
        size_str: Size string like "200MB", "1.5GB", "500KB"

    Returns:
        Size in bytes

    Raises:
        ValueError: If size format is invalid
    """
    size_str = size_str.strip().upper()

    # Extract number and unit - require numeric value
    match = re.match(r"^([\d.]+)\s*([KMGT]?B?)$", size_str)
    if not match:
        raise ValueError(
            f"Invalid size format: {size_str}. Expected format: '200MB', '1.5GB', etc."
        )

    value = float(match.group(1))
    unit = match.group(2)

    # Convert to bytes
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4,
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
    }

    if not unit:
        unit = "B"

    if unit not in multipliers:
        raise ValueError(f"Unknown size unit: {unit}")

    return int(value * multipliers[unit])


def extract_and_validate_entities(
    entities: dict[str, str], whitelist: list[str] | None = None
) -> dict[str, Any]:
    """Extract and validate entities from LLM response.

    Args:
        entities: Raw entities dict from LLM
        whitelist: Optional path whitelist for validation

    Returns:
        Validated and processed entities dict
    """
    validated = {}

    for key, value in entities.items():
        # Handle file paths
        if "path" in key.lower():
            try:
                validated[key] = validate_file_path(value, whitelist)
            except ValueError:
                # If validation fails, keep the original value
                # The agent will handle the error
                validated[key] = value

        # Handle size thresholds
        elif "size" in key.lower() and isinstance(value, str):
            try:
                # Keep both the original string and parsed bytes
                validated[key] = value
                validated[f"{key}_bytes"] = parse_size_to_bytes(value)
            except ValueError:
                validated[key] = value

        else:
            validated[key] = value

    return validated
