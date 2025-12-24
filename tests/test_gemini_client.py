"""Tests for Gemini client."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from max_os.core.gemini_client import GeminiClient


@pytest.fixture
def mock_genai():
    """Mock google.generativeai module."""
    with patch("max_os.core.gemini_client.genai") as mock:
        # Mock GenerativeModel
        mock_model = MagicMock()
        mock.GenerativeModel.return_value = mock_model

        # Mock response
        mock_response = MagicMock()
        mock_response.text = "Test response from Gemini"
        mock_model.generate_content.return_value = mock_response

        # Mock chat
        mock_chat = MagicMock()
        mock_chat.send_message.return_value = mock_response
        mock_model.start_chat.return_value = mock_chat

        yield mock


@pytest.mark.asyncio
async def test_gemini_client_init(mock_genai):
    """Test Gemini client initialization."""
    client = GeminiClient(api_key="test-key", user_id="test-user")

    assert client.api_key == "test-key"
    assert client.user_id == "test-user"
    assert client.model_name == "gemini-1.5-pro"
    assert client.max_tokens == 8192
    assert client.temperature == 0.1
    assert client.timeout == 30


@pytest.mark.asyncio
async def test_gemini_text_only(mock_genai):
    """Test text-only request."""
    client = GeminiClient(api_key="test-key")

    response = await client.process(text="What is the weather?")

    assert response == "Test response from Gemini"
    assert len(client.chat_history) == 2
    assert client.chat_history[0]["role"] == "user"
    assert client.chat_history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_gemini_multimodal_with_image(mock_genai):
    """Test multimodal request with image."""
    with patch("max_os.core.gemini_client.Image") as mock_image:
        mock_img = MagicMock()
        mock_image.open.return_value = mock_img

        client = GeminiClient(api_key="test-key")
        response = await client.process(text="What's in this image?", image="test.jpg")

        assert response == "Test response from Gemini"
        mock_image.open.assert_called_once_with("test.jpg")


@pytest.mark.asyncio
async def test_gemini_timeout(mock_genai):
    """Test request timeout."""
    mock_genai.GenerativeModel.return_value.generate_content.side_effect = asyncio.TimeoutError()

    client = GeminiClient(api_key="test-key", timeout_seconds=1)

    with pytest.raises(asyncio.TimeoutError, match="timed out after 1s"):
        await client.process(text="Test")


@pytest.mark.asyncio
async def test_gemini_api_error(mock_genai):
    """Test API error handling."""
    mock_genai.GenerativeModel.return_value.generate_content.side_effect = Exception("API Error")

    client = GeminiClient(api_key="test-key")

    with pytest.raises(RuntimeError, match="Gemini API error"):
        await client.process(text="Test")


@pytest.mark.asyncio
async def test_gemini_no_api_key():
    """Test client without API key."""
    with patch("max_os.core.gemini_client.genai"):
        client = GeminiClient(api_key="")

        with pytest.raises(RuntimeError, match="not configured"):
            await client.process(text="Test")


@pytest.mark.asyncio
async def test_gemini_context_management(mock_genai):
    """Test conversation context management."""
    client = GeminiClient(api_key="test-key")

    # First message
    await client.process(text="Hello")
    assert len(client.chat_history) == 2

    # Second message
    await client.process(text="How are you?")
    assert len(client.chat_history) == 4

    # Get history
    history = client.get_history()
    assert len(history) == 4

    # Clear history
    client.clear_history()
    assert len(client.chat_history) == 0


@pytest.mark.asyncio
async def test_gemini_generate_with_context(mock_genai):
    """Test generation with conversation context."""
    client = GeminiClient(api_key="test-key")

    # Provide custom context
    context = [
        {"role": "user", "content": "What's my name?"},
        {"role": "model", "content": "I don't have access to your name."},
    ]

    response = await client.generate_with_context("Tell me a joke", context=context)

    assert response == "Test response from Gemini"
    mock_genai.GenerativeModel.return_value.start_chat.assert_called()


@pytest.mark.asyncio
async def test_gemini_no_input():
    """Test error when no input provided."""
    with patch("max_os.core.gemini_client.genai"):
        client = GeminiClient(api_key="test-key")

        with pytest.raises(ValueError, match="At least one input type"):
            await client.process()


@pytest.mark.asyncio
async def test_gemini_with_audio(mock_genai):
    """Test audio input processing."""
    client = GeminiClient(api_key="test-key")
    audio_bytes = b"fake audio data"

    response = await client.process(audio=audio_bytes)

    assert response == "Test response from Gemini"


@pytest.mark.asyncio
async def test_gemini_with_video(mock_genai):
    """Test video input processing."""
    client = GeminiClient(api_key="test-key")
    video_bytes = b"fake video data"

    response = await client.process(video=video_bytes)

    assert response == "Test response from Gemini"


@pytest.mark.asyncio
async def test_gemini_with_system_prompt(mock_genai):
    """Test generation with system prompt."""
    client = GeminiClient(api_key="test-key")

    response = await client.process(text="Hello", system_prompt="You are a helpful assistant.")

    assert response == "Test response from Gemini"
    mock_genai.GenerativeModel.return_value.start_chat.assert_called()
