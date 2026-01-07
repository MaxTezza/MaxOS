"""Integration tests for OpenAI API.

These tests make real API calls and require OPENAI_API_KEY.
They are skipped in CI/CD by default.
"""

import os
import pytest

# Test configuration
TEST_MODEL = "gpt-4o-mini"
TEST_MAX_TOKENS = 50


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_openai_api_connection():
    """Test real connection to OpenAI API."""
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    completion = client.chat.completions.create(
        model=TEST_MODEL,
        max_tokens=TEST_MAX_TOKENS,
        messages=[{"role": "user", "content": "Say 'test' and nothing else"}],
    )

    assert completion.choices
    assert len(completion.choices) > 0
    assert "test" in completion.choices[0].message.content.lower()


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_llm_client_with_real_openai():
    """Test LLMClient with real OpenAI API."""
    from max_os.core.llm import LLMClient
    from max_os.utils.config import Settings

    settings = Settings()
    settings.orchestrator = {"provider": "openai", "model": TEST_MODEL}
    settings.llm = {
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
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
