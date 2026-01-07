"""Shared test fixtures and configuration for MaxOS tests."""

import os
import pytest
from unittest.mock import AsyncMock, Mock, patch


@pytest.fixture(autouse=True)
def mock_api_keys():
    """Automatically mock all API keys for all tests to prevent accidental real API calls."""
    with patch.dict(
        os.environ,
        {
            "ANTHROPIC_API_KEY": "test-anthropic-key-fake",
            "OPENAI_API_KEY": "test-openai-key-fake",
            "GOOGLE_API_KEY": "test-google-key-fake",
        },
        clear=False,
    ):
        yield


@pytest.fixture
def mock_anthropic_client():
    """Fixture for mocked Anthropic client.

    Example usage:
        def test_something(mock_anthropic_client):
            with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
                # Your test code
    """
    mock_client = Mock()
    mock_message = Mock()
    mock_message.content = [Mock(text="Mocked Anthropic response")]
    mock_client.messages.create.return_value = mock_message
    return mock_client


@pytest.fixture
def mock_openai_client():
    """Fixture for mocked OpenAI client.

    Example usage:
        def test_something(mock_openai_client):
            with patch('openai.OpenAI', return_value=mock_openai_client):
                # Your test code
    """
    mock_client = Mock()
    mock_choice = Mock()
    mock_choice.message.content = "Mocked OpenAI response"
    mock_completion = Mock()
    mock_completion.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_completion
    return mock_client


@pytest.fixture
def mock_gemini_client():
    """Fixture for mocked Google Gemini client.

    Example usage:
        def test_something(mock_gemini_client):
            with patch('google.generativeai.GenerativeModel', return_value=mock_gemini_client):
                # Your test code
    """
    mock_model = Mock()
    mock_response = Mock()
    mock_response.text = "Mocked Gemini response"
    mock_model.generate_content.return_value = mock_response
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
    return mock_model


@pytest.fixture
def mock_llm_client():
    """Fixture for mocked LLMClient that returns stub responses."""
    mock_client = Mock()
    mock_client.generate = Mock(return_value="[stub-response] Mocked LLM response")
    mock_client.generate_async = AsyncMock(return_value="[stub-response] Mocked LLM response")
    mock_client._has_anthropic = Mock(return_value=False)
    mock_client._has_openai = Mock(return_value=False)
    mock_client._has_google = Mock(return_value=False)
    mock_client.provider = "stub"
    return mock_client
