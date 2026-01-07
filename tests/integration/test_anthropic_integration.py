"""Integration tests for Anthropic Claude API.

These tests make real API calls and require ANTHROPIC_API_KEY.
They are skipped in CI/CD by default.
"""

import os
import pytest

# Test configuration
TEST_MODEL = "claude-3-5-sonnet-20241022"
TEST_MAX_TOKENS = 100


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
def test_anthropic_api_connection():
    """Test real connection to Anthropic API."""
    from anthropic import Anthropic

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    message = client.messages.create(
        model=TEST_MODEL,
        max_tokens=TEST_MAX_TOKENS,
        messages=[{"role": "user", "content": "Say 'test' and nothing else"}],
    )

    assert message.content
    assert len(message.content) > 0
    assert "test" in message.content[0].text.lower()


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
def test_llm_client_with_real_anthropic():
    """Test LLMClient with real Anthropic API."""
    from max_os.core.llm import LLMClient
    from max_os.utils.config import Settings

    settings = Settings()
    settings.orchestrator = {"provider": "anthropic", "model": TEST_MODEL}
    settings.llm = {
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "max_tokens": TEST_MAX_TOKENS,
        "temperature": 0.1,
        "timeout_seconds": 30,
    }

    client = LLMClient(settings)
    response = client.generate(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say 'hello' and nothing else.",
    )

    assert response
    assert "hello" in response.lower()
