"""Tests for multi-agent orchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from max_os.core.multi_agent_orchestrator import MultiAgentOrchestrator
from max_os.models.multi_agent import (
    AgentResult,
    ManagerReview,
    AgentDebateResponse,
    ConsensusCheck,
    DebateLog,
)


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "google_api_key": "test-api-key",
        "max_debate_rounds": 3,
        "consensus_threshold": 0.8,
    }


@pytest.fixture
def mock_gemini_client():
    """Mock GeminiClient for testing."""
    with patch("max_os.core.multi_agent_orchestrator.GeminiClient") as mock:
        client_instance = MagicMock()
        client_instance.process = AsyncMock()
        mock.return_value = client_instance
        yield client_instance


@pytest.mark.asyncio
async def test_agent_selection(mock_config):
    """Test manager selects appropriate agents."""
    with patch("max_os.core.multi_agent_orchestrator.GeminiClient") as mock_client:
        manager_instance = MagicMock()
        manager_instance.process = AsyncMock(
            return_value='["planning", "budget"]'
        )
        mock_client.return_value = manager_instance
        
        orchestrator = MultiAgentOrchestrator(mock_config)
        
        agents = await orchestrator._select_agents(
            "Plan a trip to Japan on $5000 budget", {}
        )
        
        assert "planning" in agents
        assert "budget" in agents


@pytest.mark.asyncio
async def test_agent_selection_fallback(mock_config):
    """Test fallback when agent selection fails."""
    with patch("max_os.core.multi_agent_orchestrator.GeminiClient") as mock_client:
        manager_instance = MagicMock()
        manager_instance.process = AsyncMock(
            side_effect=Exception("API error")
        )
        mock_client.return_value = manager_instance
        
        orchestrator = MultiAgentOrchestrator(mock_config)
        
        agents = await orchestrator._select_agents("Test query", {})
        
        # Should fall back to research agent
        assert agents == ["research"]


@pytest.mark.asyncio
async def test_parallel_execution(mock_config):
    """Test agents run in parallel."""
    with patch("max_os.core.multi_agent_orchestrator.GeminiClient") as mock_client:
        client_instance = MagicMock()
        client_instance.process = AsyncMock(return_value="Test response")
        mock_client.return_value = client_instance
        
        orchestrator = MultiAgentOrchestrator(mock_config)
        
        import time
        start = time.time()
        
        results = await orchestrator._run_agents_parallel(
            ["research", "budget", "planning"], "Plan a trip", {}
        )
        
        duration = time.time() - start
        
        # Should be faster than sequential (< 1 second for 3 agents)
        assert duration < 1.0
        assert len(results) == 3
        assert all(isinstance(r, AgentResult) for r in results)


@pytest.mark.asyncio
async def test_agent_failure_handling(mock_config):
    """Test graceful handling of agent failures."""
    with patch("max_os.core.multi_agent_orchestrator.GeminiClient") as mock_client:
        client_instance = MagicMock()
        
        # Mock one agent failing
        async def mock_process(*args, **kwargs):
            raise Exception("Agent failed")
        
        client_instance.process = mock_process
        mock_client.return_value = client_instance
        
        orchestrator = MultiAgentOrchestrator(mock_config)
        
        results = await orchestrator._run_agents_parallel(
            ["research"], "Test query", {}
        )
        
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error is not None


@pytest.mark.asyncio
async def test_manager_review_no_debate(mock_config):
    """Test manager review when no debate is needed."""
    with patch("max_os.core.multi_agent_orchestrator.GeminiClient") as mock_client:
        manager_instance = MagicMock()
        manager_instance.process = AsyncMock(
            return_value='{"needs_debate": false, "conflicts": [], "synthesis": "Final answer", "confidence": 0.9}'
        )
        mock_client.return_value = manager_instance
        
        orchestrator = MultiAgentOrchestrator(mock_config)
        
        agent_results = [
            AgentResult("research", True, "Answer 1", 0.8),
            AgentResult("budget", True, "Answer 2", 0.9),
        ]
        
        review = await orchestrator._manager_review("Test query", agent_results)
        
        assert isinstance(review, ManagerReview)
        assert review.needs_debate is False
        assert review.synthesis == "Final answer"
        assert review.confidence == 0.9


@pytest.mark.asyncio
async def test_manager_review_with_debate(mock_config):
    """Test manager review when debate is needed."""
    with patch("max_os.core.multi_agent_orchestrator.GeminiClient") as mock_client:
        manager_instance = MagicMock()
        manager_instance.process = AsyncMock(
            return_value='{"needs_debate": true, "conflicts": ["Research says X, Budget says Y"], "synthesis": null, "confidence": 0.5}'
        )
        mock_client.return_value = manager_instance
        
        orchestrator = MultiAgentOrchestrator(mock_config)
        
        agent_results = [
            AgentResult("research", True, "Buy now", 0.8),
            AgentResult("budget", True, "Wait 6 months", 0.9),
        ]
        
        review = await orchestrator._manager_review("Should I buy?", agent_results)
        
        assert review.needs_debate is True
        assert len(review.conflicts) > 0


@pytest.mark.asyncio
async def test_debate_mechanism(mock_config):
    """Test agents debate contradictions."""
    with patch("max_os.core.multi_agent_orchestrator.GeminiClient") as mock_client:
        client_instance = MagicMock()
        
        # Mock responses for debate and consensus check
        call_count = [0]
        
        async def mock_process(*args, **kwargs):
            call_count[0] += 1
            # First call is defense, second is consensus check
            if call_count[0] == 1:
                return "I maintain my position because..."
            else:
                return '{"reached": true, "final_answer": "Consensus reached", "reasoning": "Agents agree"}'
        
        client_instance.process = mock_process
        mock_client.return_value = client_instance
        
        orchestrator = MultiAgentOrchestrator(mock_config)
        
        conflicting_results = [
            AgentResult("research", True, "Buy now", 0.8),
            AgentResult("budget", True, "Wait 6 months", 0.9),
        ]
        
        debate = await orchestrator._run_debate(
            "Should I buy?", conflicting_results, ["Research says buy, Budget says wait"]
        )
        
        assert isinstance(debate, DebateLog)
        assert debate.consensus is not None
        assert debate.rounds_needed <= 3


@pytest.mark.asyncio
async def test_executive_decision(mock_config):
    """Test manager makes executive decision after max rounds."""
    with patch("max_os.core.multi_agent_orchestrator.GeminiClient") as mock_client:
        client_instance = MagicMock()
        
        # Mock consensus check always returning False
        async def mock_process(*args, **kwargs):
            prompt = str(args[0]) if args else ""
            if "Has consensus been reached" in prompt:
                return '{"reached": false, "final_answer": null, "reasoning": "No agreement"}'
            elif "make the final executive decision" in prompt:
                return "Executive decision: Buy now based on research"
            else:
                return "Defense of position"
        
        client_instance.process = mock_process
        mock_client.return_value = client_instance
        
        orchestrator = MultiAgentOrchestrator(mock_config)
        
        conflicting_results = [
            AgentResult("research", True, "Buy now", 0.8),
            AgentResult("budget", True, "Wait", 0.9),
        ]
        
        debate = await orchestrator._run_debate(
            "Should I buy?", conflicting_results, ["Conflict"]
        )
        
        assert debate.executive_decision is True
        assert debate.rounds_needed == 3
        assert "Executive decision" in debate.consensus


@pytest.mark.asyncio
async def test_show_work_logs(mock_config):
    """Test user can see all agent work."""
    with patch("max_os.core.multi_agent_orchestrator.GeminiClient") as mock_client:
        client_instance = MagicMock()
        
        async def mock_process(*args, **kwargs):
            prompt = str(args[0]) if args else ""
            if "Which agents should work" in prompt:
                return '["research"]'
            elif "Analyze these results" in prompt:
                return '{"needs_debate": false, "conflicts": [], "synthesis": "Final answer", "confidence": 0.9}'
            else:
                return "Agent response"
        
        client_instance.process = mock_process
        mock_client.return_value = client_instance
        
        orchestrator = MultiAgentOrchestrator(mock_config)
        
        result = await orchestrator.process_with_debate(
            "Complex query", show_work=True
        )
        
        assert result.agent_work_logs is not None
        assert len(result.agent_work_logs) > 0


@pytest.mark.asyncio
async def test_no_work_logs_when_disabled(mock_config):
    """Test work logs are not returned when show_work=False."""
    with patch("max_os.core.multi_agent_orchestrator.GeminiClient") as mock_client:
        client_instance = MagicMock()
        
        async def mock_process(*args, **kwargs):
            prompt = str(args[0]) if args else ""
            if "Which agents should work" in prompt:
                return '["research"]'
            elif "Analyze these results" in prompt:
                return '{"needs_debate": false, "conflicts": [], "synthesis": "Final answer", "confidence": 0.9}'
            else:
                return "Agent response"
        
        client_instance.process = mock_process
        mock_client.return_value = client_instance
        
        orchestrator = MultiAgentOrchestrator(mock_config)
        
        result = await orchestrator.process_with_debate(
            "Complex query", show_work=False
        )
        
        assert result.agent_work_logs is None


@pytest.mark.asyncio
async def test_process_with_context(mock_config):
    """Test processing with context."""
    with patch("max_os.core.multi_agent_orchestrator.GeminiClient") as mock_client:
        client_instance = MagicMock()
        
        context_received = []
        
        async def mock_process(*args, **kwargs):
            prompt = str(args[0]) if args else ""
            if "Context:" in prompt:
                context_received.append(True)
            if "Which agents should work" in prompt:
                return '["research"]'
            elif "Analyze these results" in prompt:
                return '{"needs_debate": false, "conflicts": [], "synthesis": "Final answer", "confidence": 0.9}'
            else:
                return "Agent response"
        
        client_instance.process = mock_process
        mock_client.return_value = client_instance
        
        orchestrator = MultiAgentOrchestrator(mock_config)
        
        result = await orchestrator.process_with_debate(
            "Test query", context={"budget": 5000, "location": "Seattle"}
        )
        
        assert len(context_received) > 0
        assert result.final_answer is not None
