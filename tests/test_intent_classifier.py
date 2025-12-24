from unittest.mock import AsyncMock, MagicMock

import pytest

from max_os.core.intent import Intent
from max_os.core.intent_classifier import IntentClassifier
from max_os.core.planner import IntentPlanner
from max_os.utils.config import Settings


@pytest.fixture
def mock_planner():
    planner = MagicMock(spec=IntentPlanner)
    planner.plan.return_value = Intent(
        name="system.general", confidence=0.2, slots=[], summary="General system request"
    )
    return planner


@pytest.fixture
def mock_settings():
    settings = MagicMock(spec=Settings)
    settings.orchestrator = {"provider": "stub", "model": "test"}
    settings.llm = {
        "fallback_to_rules": True,
        "max_tokens": 500,
        "temperature": 0.1,
        "timeout_seconds": 10,
    }
    settings.agents = {}
    return settings


@pytest.fixture
def intent_classifier(mock_planner, mock_settings):
    return IntentClassifier(planner=mock_planner, settings=mock_settings)


@pytest.mark.asyncio
async def test_classify_dev_commit_with_modified_git_status(intent_classifier, mock_planner):
    context = {"git_status": "modified"}
    prompt = "commit my changes"

    intent = await intent_classifier.classify(prompt, context)

    assert intent.name == "dev.commit"
    assert intent.confidence == 0.9
    assert intent.summary == "User wants to commit/push changes"
    mock_planner.plan.assert_not_called()  # Should not fall back to planner


@pytest.mark.asyncio
async def test_classify_fallback_to_planner(intent_classifier, mock_planner):
    context = {"git_status": "clean"}
    prompt = "list files"

    # Configure mock_planner to return a specific intent for "list files"
    mock_planner.plan.return_value = Intent(
        name="file.list", confidence=0.65, slots=[], summary="List directory contents"
    )

    intent = await intent_classifier.classify(prompt, context)

    assert intent.name == "file.list"
    assert intent.confidence == 0.65
    assert intent.summary == "List directory contents"
    mock_planner.plan.assert_called_once_with(prompt, {"git_status": "clean"})


@pytest.mark.asyncio
async def test_classify_no_match_falls_back_to_default(intent_classifier, mock_planner):
    context = {"git_status": "clean"}
    prompt = "unrecognized command"

    # Planner's default return value is "system.general"
    intent = await intent_classifier.classify(prompt, context)

    assert intent.name == "system.general"
    assert intent.confidence == 0.2
    assert intent.summary == "General system request"
    mock_planner.plan.assert_called_once_with(prompt, {"git_status": "clean"})


@pytest.mark.asyncio
async def test_classify_with_llm_success(mock_planner, mock_settings):
    """Test successful LLM classification."""
    # Configure settings to use LLM
    mock_settings.orchestrator = {"provider": "anthropic", "model": "claude-3-5-sonnet"}

    # Create mock LLM client
    mock_llm = MagicMock()
    mock_llm._has_anthropic.return_value = True
    mock_llm.generate_async = AsyncMock(
        return_value='{"intent": "file.search", "confidence": 0.95, "entities": {"search_query": "test"}}'
    )

    classifier = IntentClassifier(planner=mock_planner, settings=mock_settings, llm_client=mock_llm)

    intent = await classifier.classify("search for test files", {})

    assert intent.name == "file.search"
    assert intent.confidence == 0.95
    assert len(intent.slots) == 1
    assert intent.slots[0].name == "search_query"
    mock_llm.generate_async.assert_called_once()
    mock_planner.plan.assert_not_called()  # Should not fall back to planner


@pytest.mark.asyncio
async def test_classify_llm_timeout_falls_back(mock_planner, mock_settings):
    """Test that LLM timeout triggers fallback to rules."""
    import asyncio

    mock_settings.orchestrator = {"provider": "anthropic", "model": "claude-3-5-sonnet"}

    mock_llm = MagicMock()
    mock_llm._has_anthropic.return_value = True
    mock_llm.generate_async = AsyncMock(side_effect=asyncio.TimeoutError("Timed out"))

    mock_planner.plan.return_value = Intent(
        name="file.list", confidence=0.65, slots=[], summary="List files"
    )

    classifier = IntentClassifier(planner=mock_planner, settings=mock_settings, llm_client=mock_llm)

    intent = await classifier.classify("list files", {})

    # Should fall back to rule-based classification
    assert intent.name == "file.list"
    mock_planner.plan.assert_called_once()


@pytest.mark.asyncio
async def test_classify_llm_error_falls_back(mock_planner, mock_settings):
    """Test that LLM error triggers fallback to rules."""
    mock_settings.orchestrator = {"provider": "anthropic", "model": "claude-3-5-sonnet"}

    mock_llm = MagicMock()
    mock_llm._has_anthropic.return_value = True
    mock_llm.generate_async = AsyncMock(side_effect=Exception("API Error"))

    mock_planner.plan.return_value = Intent(
        name="system.health", confidence=0.65, slots=[], summary="System health"
    )

    classifier = IntentClassifier(planner=mock_planner, settings=mock_settings, llm_client=mock_llm)

    intent = await classifier.classify("show system health", {})

    # Should fall back to rule-based classification
    assert intent.name == "system.health"
    mock_planner.plan.assert_called_once()


@pytest.mark.asyncio
async def test_should_use_llm_with_stub_provider(mock_planner, mock_settings):
    """Test that stub provider disables LLM."""
    mock_settings.orchestrator = {"provider": "stub"}
    classifier = IntentClassifier(planner=mock_planner, settings=mock_settings)

    assert classifier.use_llm is False


@pytest.mark.asyncio
async def test_should_use_llm_with_anthropic(mock_planner, mock_settings):
    """Test that anthropic provider with API key enables LLM."""
    mock_settings.orchestrator = {"provider": "anthropic"}

    mock_llm = MagicMock()
    mock_llm._has_anthropic.return_value = True

    classifier = IntentClassifier(planner=mock_planner, settings=mock_settings, llm_client=mock_llm)

    assert classifier.use_llm is True
