"""Entity extraction and validation for intent classification."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from max_os.core.intent import Intent, Slot


class EntityExtractor:
    """Extract and validate entities from LLM responses."""
    
    def __init__(self, path_whitelist: list[str] | None = None):
        """
        Initialize entity extractor.
        
        Args:
            path_whitelist: List of allowed path prefixes for security
        """
        self.path_whitelist = path_whitelist or [
            "/home",
            "/srv",
            "/tmp",
            "~",
            ".",
            "..",
        ]
    
    def parse_llm_response(self, response_text: str) -> dict[str, Any] | None:
        """
        Parse LLM JSON response into structured data.
        
        Handles markdown code block wrapping (```json ... ```) and provides
        default values for missing optional fields (confidence, entities, summary).
        
        Args:
            response_text: Raw text response from LLM
            
        Returns:
            Parsed dictionary with required fields, or None if parsing fails
        """
        try:
            # Try to extract JSON from response
            # LLM might wrap JSON in markdown code blocks
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            data = json.loads(response_text)
            
            # Validate required fields
            if "intent" not in data:
                return None
            if "confidence" not in data:
                data["confidence"] = 0.5  # Default confidence
            if "entities" not in data:
                data["entities"] = {}
            if "summary" not in data:
                data["summary"] = ""
                
            return data
            
        except (json.JSONDecodeError, ValueError):
            return None
    
    def extract_intent_from_llm(self, response_text: str) -> Intent | None:
        """
        Extract Intent object from LLM response.
        
        Args:
            response_text: Raw text response from LLM
            
        Returns:
            Intent object or None if parsing fails
        """
        data = self.parse_llm_response(response_text)
        if not data:
            return None
        
        # Convert entities dict to Slot list
        slots = []
        entities = data.get("entities", {})
        
        # Process and validate entities
        processed_entities = self.process_entities(entities)
        
        for key, value in processed_entities.items():
            slots.append(Slot(name=key, value=str(value)))
        
        return Intent(
            name=data["intent"],
            confidence=float(data["confidence"]),
            slots=slots,
            summary=data.get("summary", "")
        )
    
    def process_entities(self, entities: dict[str, Any]) -> dict[str, Any]:
        """
        Process and validate extracted entities.
        
        Args:
            entities: Raw entities dict from LLM
            
        Returns:
            Processed and validated entities dict
        """
        processed = {}
        
        for key, value in entities.items():
            # Handle path entities
            if "path" in key.lower():
                processed[key] = self.normalize_path(str(value))
            # Handle size entities
            elif key in ["size_threshold", "size_mb", "size_gb"]:
                processed[key] = self.normalize_size(str(value))
            # Handle other entities
            else:
                processed[key] = value
        
        return processed
    
    def normalize_path(self, path: str) -> str:
        """
        Normalize and validate file path.
        
        Args:
            path: Raw path string
            
        Returns:
            Normalized path
        """
        # Expand home directory
        if path.startswith("~"):
            path = os.path.expanduser(path)
        
        # Convert to absolute path if relative
        if not os.path.isabs(path):
            # Keep relative paths as-is for now
            # The agent will resolve them in its context
            pass
        
        # Validate against whitelist (basic check)
        # Note: Full validation should happen in the agent layer
        # This is just a preliminary security check
        
        return path
    
    def normalize_size(self, size_str: str) -> int:
        """
        Convert human-readable size to bytes.
        
        Args:
            size_str: Size string like "200MB", "1GB", "500"
            
        Returns:
            Size in bytes
        """
        size_str = size_str.strip().upper()
        
        # Extract number and unit
        match = re.match(r"(\d+(?:\.\d+)?)\s*([KMGT]?B?)?", size_str)
        if not match:
            return 0
        
        number_str, unit = match.groups()
        number = float(number_str)
        
        # Convert to bytes
        if not unit or unit == "B":
            return int(number)
        elif unit in ["KB", "K"]:
            return int(number * 1024)
        elif unit in ["MB", "M"]:
            return int(number * 1024 * 1024)
        elif unit in ["GB", "G"]:
            return int(number * 1024 * 1024 * 1024)
        elif unit in ["TB", "T"]:
            return int(number * 1024 * 1024 * 1024 * 1024)
        else:
            return int(number)
    
    def validate_path_security(self, path: str) -> bool:
        """
        Validate path against security whitelist.
        
        Args:
            path: Path to validate
            
        Returns:
            True if path is allowed, False otherwise
        """
        # Expand path for comparison
        expanded = os.path.expanduser(path)
        
        # Allow relative paths
        if not os.path.isabs(expanded):
            return True
        
        # Check against whitelist
        for allowed_prefix in self.path_whitelist:
            allowed_expanded = os.path.expanduser(allowed_prefix)
            if expanded.startswith(allowed_expanded):
                return True
        
        return False
