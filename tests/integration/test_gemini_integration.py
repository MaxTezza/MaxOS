"""Integration tests for Google Gemini API.

These tests make real API calls and require GOOGLE_API_KEY.
They are skipped in CI/CD by default.
"""

import os
import pytest


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set")
@pytest.mark.asyncio
async def test_gemini_client_real_api():
    """Test GeminiClient with real Google API."""
    pytest.importorskip("google.generativeai")

    from max_os.core.gemini_client import GeminiClient

    client = GeminiClient(
        model="gemini-1.5-flash",
        api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.2,
        max_tokens=100,
    )

    response = await client.process("Say 'test' and nothing else")

    assert response
    assert "test" in response.lower()


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set")
def test_gemini_client_sync_real_api():
    """Test GeminiClient synchronous method with real Google API."""
    pytest.importorskip("google.generativeai")

    from max_os.core.gemini_client import GeminiClient

    client = GeminiClient(
        model="gemini-1.5-flash",
        api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.2,
        max_tokens=100,
    )

    response = client.process_sync("Say 'hello' and nothing else")

    assert response
    assert "hello" in response.lower()
