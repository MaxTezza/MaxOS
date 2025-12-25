"""Tests for prompt generation."""

from max_os.core.prompts import build_user_prompt, get_system_prompt


def test_get_system_prompt():
    """Test that system prompt is returned correctly."""
    prompt = get_system_prompt()

    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "MaxOS" in prompt
    assert "intent" in prompt.lower()
    assert "entities" in prompt.lower()

    # Check that it mentions some key intents
    assert "file.search" in prompt
    assert "system.health" in prompt
    assert "dev.git_status" in prompt
    assert "network.ping" in prompt


def test_build_user_prompt_without_context():
    """Test building user prompt without context."""
    user_input = "show system health"
    prompt = build_user_prompt(user_input)

    assert user_input in prompt
    assert "User request:" in prompt
    assert "Classify this intent" in prompt


def test_build_user_prompt_with_git_context():
    """Test building user prompt with git status context."""
    user_input = "commit my changes"
    context = {"git_status": "modified"}
    prompt = build_user_prompt(user_input, context)

    assert user_input in prompt
    assert "Git status: modified" in prompt
    assert "User request:" in prompt


def test_build_user_prompt_with_active_window_context():
    """Test building user prompt with active window context."""
    user_input = "save this file"
    context = {"active_window": "VSCode"}
    prompt = build_user_prompt(user_input, context)

    assert user_input in prompt
    assert "Active window: VSCode" in prompt


def test_build_user_prompt_with_multiple_context():
    """Test building user prompt with multiple context values."""
    user_input = "commit and push"
    context = {"git_status": "modified", "active_window": "Terminal"}
    prompt = build_user_prompt(user_input, context)

    assert user_input in prompt
    assert "Git status: modified" in prompt
    assert "Active window: Terminal" in prompt


def test_build_user_prompt_with_empty_context():
    """Test that empty context is handled correctly."""
    user_input = "list files"
    context = {}
    prompt = build_user_prompt(user_input, context)

    # Should be same as no context
    assert user_input in prompt
    assert "User request:" in prompt
    # Should not have any context info
    assert "Git status:" not in prompt
    assert "Active window:" not in prompt
