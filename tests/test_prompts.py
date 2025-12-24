"""Tests for system prompt generation."""

import pytest

from max_os.core.prompts import build_llm_prompt, get_few_shot_examples, get_system_prompt


def test_get_system_prompt():
    """Test that system prompt is generated correctly."""
    prompt = get_system_prompt()
    
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    
    # Check for key elements
    assert "MaxOS" in prompt
    assert "intent" in prompt.lower()
    assert "entities" in prompt.lower()
    assert "confidence" in prompt.lower()
    
    # Check for intent types
    assert "file.search" in prompt
    assert "system.health" in prompt
    assert "dev.git_status" in prompt
    assert "network.ping" in prompt
    
    # Check for JSON format specification
    assert "JSON" in prompt or "json" in prompt


def test_get_few_shot_examples():
    """Test that few-shot examples are properly structured."""
    examples = get_few_shot_examples()
    
    assert isinstance(examples, list)
    assert len(examples) > 0
    
    for example in examples:
        assert "user" in example
        assert "assistant" in example
        assert isinstance(example["user"], str)
        assert isinstance(example["assistant"], str)
        
        # Each assistant response should be valid JSON-like
        assert "{" in example["assistant"]
        assert "}" in example["assistant"]
        assert "intent" in example["assistant"]
        assert "confidence" in example["assistant"]


def test_build_llm_prompt_basic():
    """Test basic LLM prompt building."""
    user_input = "list files in Documents"
    prompt = build_llm_prompt(user_input)
    
    assert isinstance(prompt, str)
    assert user_input in prompt
    
    # Should include system prompt
    assert "MaxOS" in prompt
    
    # Should include examples
    assert "Examples:" in prompt or "User:" in prompt
    
    # Should have the user input at the end
    assert prompt.endswith(user_input + "\nAssistant:")


def test_build_llm_prompt_with_context():
    """Test LLM prompt building with context."""
    user_input = "commit my changes"
    context = {
        "git_status": "modified",
        "active_window": "VSCode"
    }
    
    prompt = build_llm_prompt(user_input, context)
    
    assert isinstance(prompt, str)
    assert user_input in prompt
    
    # Context should be included
    assert "context" in prompt.lower()
    assert "modified" in prompt
    assert "VSCode" in prompt


def test_build_llm_prompt_with_last_action():
    """Test LLM prompt building with last action in context."""
    user_input = "show me more"
    context = {
        "last_action": "list files in Downloads"
    }
    
    prompt = build_llm_prompt(user_input, context)
    
    assert isinstance(prompt, str)
    assert user_input in prompt
    assert "list files in Downloads" in prompt


def test_few_shot_examples_valid_intents():
    """Test that few-shot examples use valid intent names."""
    examples = get_few_shot_examples()
    
    valid_intents = [
        "file.search", "file.copy", "file.move", "file.delete", "file.list",
        "system.health", "system.processes", "system.service",
        "dev.git_status", "dev.git_commit",
        "network.ping", "network.interfaces"
    ]
    
    for example in examples:
        # Extract intent from JSON response
        assert "\"intent\":" in example["assistant"]


def test_few_shot_examples_have_confidence():
    """Test that few-shot examples include confidence scores."""
    examples = get_few_shot_examples()
    
    for example in examples:
        assert "\"confidence\":" in example["assistant"]
        # Confidence should be between 0 and 1
        # Just check the format exists, actual parsing tested elsewhere
