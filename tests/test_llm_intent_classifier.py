"""Tests for LLM-powered intent classification."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from max_os.core.intent import Intent
from max_os.core.intent_classifier import IntentClassifier
from max_os.core.planner import IntentPlanner
from max_os.utils.llm_api import LLMAPI


@pytest.fixture
def mock_llm_api():
    """Create a mock LLM API."""
    llm = MagicMock(spec=LLMAPI)
    llm.is_available.return_value = True
    llm.generate_text = AsyncMock()
    return llm


@pytest.fixture
def mock_planner():
    """Create a mock planner for fallback."""
    planner = MagicMock(spec=IntentPlanner)
    planner.plan.return_value = Intent(
        name="system.general",
        confidence=0.2,
        slots=[],
        summary="General system request"
    )
    return planner


@pytest.fixture
def intent_classifier(mock_planner, mock_llm_api):
    """Create intent classifier with mocked dependencies."""
    return IntentClassifier(
        planner=mock_planner,
        llm_api=mock_llm_api,
        fallback_to_rules=True
    )


@pytest.mark.asyncio
async def test_classify_with_llm_success(intent_classifier, mock_llm_api):
    """Test successful classification using LLM."""
    # Mock LLM response
    llm_response = """{
  "intent": "file.copy",
  "confidence": 0.95,
  "entities": {
    "source_path": "Documents/report.pdf",
    "dest_path": "Backup"
  },
  "summary": "Copy report.pdf to Backup"
}"""
    mock_llm_api.generate_text.return_value = llm_response
    
    prompt = "copy Documents/report.pdf to Backup folder"
    context = {}
    
    intent = await intent_classifier.classify(prompt, context)
    
    assert intent is not None
    assert intent.name == "file.copy"
    assert intent.confidence == 0.95
    assert len(intent.slots) == 2
    assert intent.summary == "Copy report.pdf to Backup"
    mock_llm_api.generate_text.assert_called_once()


@pytest.mark.asyncio
async def test_classify_with_llm_context_awareness(intent_classifier, mock_llm_api):
    """Test LLM classification with context."""
    llm_response = """{
  "intent": "dev.git_commit",
  "confidence": 0.92,
  "entities": {},
  "summary": "Commit changes"
}"""
    mock_llm_api.generate_text.return_value = llm_response
    
    prompt = "commit my work"
    context = {"git_status": "modified"}
    
    intent = await intent_classifier.classify(prompt, context)
    
    assert intent is not None
    assert intent.name == "dev.git_commit"
    mock_llm_api.generate_text.assert_called_once()


@pytest.mark.asyncio
async def test_classify_fallback_to_rules_on_llm_failure(intent_classifier, mock_llm_api, mock_planner):
    """Test fallback to rule-based classification when LLM fails."""
    # Make LLM raise an exception
    mock_llm_api.generate_text.side_effect = Exception("API timeout")
    
    # Configure planner to return specific intent
    mock_planner.plan.return_value = Intent(
        name="file.manage",
        confidence=0.65,
        slots=[],
        summary="File management"
    )
    
    prompt = "manage files"
    context = {}
    
    intent = await intent_classifier.classify(prompt, context)
    
    assert intent is not None
    assert intent.name == "file.manage"
    assert intent.confidence == 0.65
    mock_planner.plan.assert_called_once()


@pytest.mark.asyncio
async def test_classify_without_llm_api():
    """Test classification when LLM API is not available."""
    planner = MagicMock(spec=IntentPlanner)
    planner.plan.return_value = Intent(
        name="system.health",
        confidence=0.65,
        slots=[],
        summary="Check system health"
    )
    
    # Create classifier without LLM API
    classifier = IntentClassifier(
        planner=planner,
        llm_api=None,
        fallback_to_rules=True
    )
    
    prompt = "show system health"
    context = {}
    
    intent = await classifier.classify(prompt, context)
    
    assert intent is not None
    assert intent.name == "system.health"
    planner.plan.assert_called_once()


@pytest.mark.asyncio
async def test_classify_with_llm_invalid_response(intent_classifier, mock_llm_api, mock_planner):
    """Test handling of invalid LLM response."""
    # LLM returns invalid JSON
    mock_llm_api.generate_text.return_value = "This is not valid JSON"
    
    mock_planner.plan.return_value = Intent(
        name="system.general",
        confidence=0.2,
        slots=[],
        summary="General request"
    )
    
    prompt = "do something"
    context = {}
    
    intent = await intent_classifier.classify(prompt, context)
    
    # Should fallback to rule-based planner
    assert intent is not None
    mock_planner.plan.assert_called_once()


@pytest.mark.asyncio
async def test_classify_with_entity_extraction(intent_classifier, mock_llm_api):
    """Test entity extraction from LLM response."""
    llm_response = """{
  "intent": "file.search",
  "confidence": 0.92,
  "entities": {
    "pattern": "*.pdf",
    "search_path": "Downloads",
    "size_threshold": "200MB"
  },
  "summary": "Search for large PDF files"
}"""
    mock_llm_api.generate_text.return_value = llm_response
    
    prompt = "search Downloads for .pdf files larger than 200MB"
    context = {}
    
    intent = await intent_classifier.classify(prompt, context)
    
    assert intent is not None
    assert intent.name == "file.search"
    assert len(intent.slots) == 3
    
    # Check slots
    slot_names = [slot.name for slot in intent.slots]
    assert "pattern" in slot_names
    assert "search_path" in slot_names


@pytest.mark.asyncio
async def test_classify_git_context_rule_based_fallback(intent_classifier, mock_llm_api):
    """Test the existing git context rule when using rule-based fallback."""
    # Make LLM unavailable
    mock_llm_api.is_available.return_value = False
    
    prompt = "commit my changes"
    context = {"git_status": "modified"}
    
    intent = await intent_classifier.classify(prompt, context)
    
    # Should use the existing context-aware rule
    assert intent is not None
    assert intent.name == "dev.commit"
    assert intent.confidence == 0.9


@pytest.mark.asyncio
async def test_classify_no_fallback_on_llm_failure():
    """Test behavior when fallback is disabled and LLM fails."""
    planner = MagicMock(spec=IntentPlanner)
    llm_api = MagicMock(spec=LLMAPI)
    llm_api.is_available.return_value = True
    llm_api.generate_text = AsyncMock(side_effect=Exception("API error"))
    
    classifier = IntentClassifier(
        planner=planner,
        llm_api=llm_api,
        fallback_to_rules=False  # Disable fallback
    )
    
    prompt = "test command"
    context = {}
    
    intent = await classifier.classify(prompt, context)
    
    # Should return low-confidence general intent
    assert intent is not None
    assert intent.name == "system.general"
    assert intent.confidence == 0.2
    planner.plan.assert_not_called()


@pytest.mark.asyncio
async def test_classify_with_confidence_scores(intent_classifier, mock_llm_api):
    """Test that confidence scores are properly preserved."""
    llm_response = """{
  "intent": "network.ping",
  "confidence": 0.96,
  "entities": {"host": "google.com"},
  "summary": "Ping google.com"
}"""
    mock_llm_api.generate_text.return_value = llm_response
    
    prompt = "ping google.com"
    context = {}
    
    intent = await intent_classifier.classify(prompt, context)
    
    assert intent.confidence == 0.96


@pytest.mark.asyncio
async def test_classify_with_multiple_entities(intent_classifier, mock_llm_api):
    """Test classification with multiple entities."""
    llm_response = """{
  "intent": "file.copy",
  "confidence": 0.94,
  "entities": {
    "source_path": "~/Documents/file.txt",
    "dest_path": "/backup",
    "operation": "copy"
  },
  "summary": "Copy file to backup"
}"""
    mock_llm_api.generate_text.return_value = llm_response
    
    prompt = "copy ~/Documents/file.txt to /backup"
    context = {}
    
    intent = await intent_classifier.classify(prompt, context)
    
    assert intent is not None
    assert len(intent.slots) == 3
