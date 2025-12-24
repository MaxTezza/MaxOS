from unittest.mock import MagicMock

import pytest

from max_os.core.intent import Intent
from max_os.core.intent_classifier import IntentClassifier
from max_os.core.planner import IntentPlanner


@pytest.fixture
def mock_planner():
    planner = MagicMock(spec=IntentPlanner)
    planner.plan.return_value = Intent(
        name="system.general", confidence=0.2, slots=[], summary="General system request"
    )
    return planner


@pytest.fixture
def intent_classifier(mock_planner):
    return IntentClassifier(planner=mock_planner)


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
