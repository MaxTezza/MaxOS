"""Integration test for multi-agent orchestrator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from max_os.core.orchestrator import AIOperatingSystem
from max_os.utils.config import Settings


@pytest.fixture
def multi_agent_settings():
    """Settings with multi-agent enabled."""
    settings = Settings()
    settings.multi_agent = {
        "enabled": True,
        "google_api_key": "test-key",
        "max_debate_rounds": 3,
        "consensus_threshold": 0.8,
        "route_complex_queries": True,
    }
    settings.llm = {"google_api_key": "test-key"}
    return settings


@pytest.mark.asyncio
@patch("redis.from_url")
async def test_complex_query_routing_to_multi_agent(mock_redis):
    """Test complex queries route to multi-agent system."""
    mock_redis.return_value = MagicMock()

    # Mock the multi-agent orchestrator at the import location
    with patch("max_os.core.multi_agent_orchestrator.MultiAgentOrchestrator") as mock_ma:
        mock_instance = MagicMock()
        mock_instance.process_with_debate = AsyncMock(
            return_value=MagicMock(
                final_answer="Test answer",
                agents_used=["research", "budget"],
                confidence=0.85,
                agent_work_logs=None,
                debate_log=None,
                manager_review=MagicMock(
                    needs_debate=False,
                    conflicts=[],
                    confidence=0.85,
                ),
            )
        )
        mock_ma.return_value = mock_instance

        settings = Settings()
        settings.multi_agent = {
            "enabled": True,
            "google_api_key": "test-key",
            "route_complex_queries": True,
        }
        settings.llm = {"google_api_key": "test-key"}

        orchestrator = AIOperatingSystem(settings=settings, enable_learning=False)

        # Complex query should route to multi-agent
        response = await orchestrator.handle_text(
            "Should I plan a trip to Japan or invest in stocks?"
        )

        assert response.agent == "multi_agent"
        assert response.status == "success"
        assert "agents_used" in response.payload


@pytest.mark.asyncio
@patch("redis.from_url")
async def test_simple_query_not_routed_to_multi_agent(mock_redis):
    """Test simple queries don't route to multi-agent system."""
    mock_redis.return_value = MagicMock()

    with patch("max_os.core.multi_agent_orchestrator.MultiAgentOrchestrator") as mock_ma:
        mock_instance = MagicMock()
        mock_instance.process_with_debate = AsyncMock()
        mock_ma.return_value = mock_instance

        settings = Settings()
        settings.multi_agent = {
            "enabled": True,
            "google_api_key": "test-key",
            "route_complex_queries": True,
        }
        settings.llm = {"google_api_key": "test-key"}

        orchestrator = AIOperatingSystem(settings=settings, enable_learning=False)

        # Simple query should not route to multi-agent
        await orchestrator.handle_text("list files")

        # Should not call multi-agent
        mock_instance.process_with_debate.assert_not_called()


@pytest.mark.asyncio
@patch("redis.from_url")
async def test_multi_agent_disabled(mock_redis):
    """Test multi-agent system is not used when disabled."""
    mock_redis.return_value = MagicMock()

    settings = Settings()
    settings.multi_agent = {"enabled": False}

    orchestrator = AIOperatingSystem(settings=settings, enable_learning=False)

    # Should not have multi-agent orchestrator
    assert orchestrator.multi_agent is None

    # Query should work normally
    response = await orchestrator.handle_text("plan a trip")
    assert response is not None


@pytest.mark.asyncio
@patch("redis.from_url")
async def test_multi_agent_fallback_on_error(mock_redis):
    """Test fallback to normal processing when multi-agent fails."""
    mock_redis.return_value = MagicMock()

    with patch("max_os.core.multi_agent_orchestrator.MultiAgentOrchestrator") as mock_ma:
        mock_instance = MagicMock()
        mock_instance.process_with_debate = AsyncMock(side_effect=Exception("Multi-agent error"))
        mock_ma.return_value = mock_instance

        settings = Settings()
        settings.multi_agent = {
            "enabled": True,
            "google_api_key": "test-key",
            "route_complex_queries": True,
        }
        settings.llm = {"google_api_key": "test-key"}

        orchestrator = AIOperatingSystem(settings=settings, enable_learning=False)

        # Should fall back to normal processing
        response = await orchestrator.handle_text("Should I plan a trip or analyze the market?")

        # Should still get a response (fallback to normal agent)
        assert response is not None
        assert response.agent != "multi_agent"
