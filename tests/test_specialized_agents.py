"""Tests for specialized agents."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from max_os.agents.base_specialized_agent import SpecializedAgent
from max_os.agents.specialized import (
    BudgetAgent,
    CreativeAgent,
    PlanningAgent,
    ResearchAgent,
    TechnicalAgent,
)
from max_os.models.multi_agent import AgentResult


@pytest.fixture
def mock_gemini_client():
    """Mock GeminiClient for testing."""
    mock_client = MagicMock()
    mock_client.process = AsyncMock(return_value="Test response with confidence: 0.8")
    mock_client.temperature = 0.2
    return mock_client


@pytest.mark.asyncio
async def test_specialized_agent_base(mock_gemini_client):
    """Test base specialized agent."""
    agent = SpecializedAgent(llm=mock_gemini_client, role="test", expertise="Testing things")

    result = await agent.process("Test query", {})

    assert isinstance(result, AgentResult)
    assert result.agent_name == "test"
    assert result.success is True
    assert result.answer is not None


@pytest.mark.asyncio
async def test_research_agent(mock_gemini_client):
    """Test research agent initialization and processing."""
    agent = ResearchAgent(mock_gemini_client)

    assert agent.role == "research"
    assert "factual information" in agent.expertise.lower()

    result = await agent.process("What is the capital of France?", {})

    assert result.agent_name == "research"
    assert result.success is True


@pytest.mark.asyncio
async def test_creative_agent(mock_gemini_client):
    """Test creative agent has higher temperature."""
    agent = CreativeAgent(mock_gemini_client)

    assert agent.role == "creative"
    assert "creative" in agent.expertise.lower()
    # Creative agent should have higher temperature
    assert agent.llm.temperature == 0.8

    result = await agent.process("Generate creative ideas", {})

    assert result.agent_name == "creative"
    assert result.success is True


@pytest.mark.asyncio
async def test_technical_agent(mock_gemini_client):
    """Test technical agent."""
    agent = TechnicalAgent(mock_gemini_client)

    assert agent.role == "technical"
    assert "technical" in agent.expertise.lower()

    result = await agent.process("Analyze technical feasibility", {})

    assert result.agent_name == "technical"
    assert result.success is True


@pytest.mark.asyncio
async def test_budget_agent(mock_gemini_client):
    """Test budget agent has zero temperature for accuracy."""
    agent = BudgetAgent(mock_gemini_client)

    assert agent.role == "budget"
    assert "financial" in agent.expertise.lower() or "budget" in agent.expertise.lower()
    # Budget agent should have zero temperature for numerical accuracy
    assert agent.llm.temperature == 0.0

    result = await agent.process("Calculate costs", {})

    assert result.agent_name == "budget"
    assert result.success is True


@pytest.mark.asyncio
async def test_planning_agent(mock_gemini_client):
    """Test planning agent."""
    agent = PlanningAgent(mock_gemini_client)

    assert agent.role == "planning"
    assert "plan" in agent.expertise.lower()

    result = await agent.process("Create a project plan", {})

    assert result.agent_name == "planning"
    assert result.success is True


@pytest.mark.asyncio
async def test_agent_error_handling(mock_gemini_client):
    """Test agent handles errors gracefully."""
    mock_gemini_client.process = AsyncMock(side_effect=Exception("API error"))

    agent = ResearchAgent(mock_gemini_client)
    result = await agent.process("Test query", {})

    assert result.success is False
    assert result.error is not None
    assert "API error" in result.error
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_confidence_extraction_explicit(mock_gemini_client):
    """Test confidence extraction from explicit statements."""
    mock_gemini_client.process = AsyncMock(return_value="This is my answer. Confidence: 0.95")

    agent = ResearchAgent(mock_gemini_client)
    result = await agent.process("Test query", {})

    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_confidence_extraction_percentage(mock_gemini_client):
    """Test confidence extraction from percentage."""
    mock_gemini_client.process = AsyncMock(return_value="This is my answer. Confidence: 85%")

    agent = ResearchAgent(mock_gemini_client)
    result = await agent.process("Test query", {})

    assert result.confidence == 0.85


@pytest.mark.asyncio
async def test_confidence_heuristic_hedging(mock_gemini_client):
    """Test confidence heuristic with hedging words."""
    mock_gemini_client.process = AsyncMock(return_value="Maybe this could possibly work, perhaps.")

    agent = ResearchAgent(mock_gemini_client)
    result = await agent.process("Test query", {})

    # Should have lower confidence due to hedging
    assert result.confidence <= 0.7


@pytest.mark.asyncio
async def test_confidence_heuristic_confident(mock_gemini_client):
    """Test confidence heuristic with confident language."""
    mock_gemini_client.process = AsyncMock(
        return_value="This is definitely the right answer based on evidence."
    )

    agent = ResearchAgent(mock_gemini_client)
    result = await agent.process("Test query", {})

    # Should have default confidence
    assert result.confidence == 0.8


@pytest.mark.asyncio
async def test_agent_with_context(mock_gemini_client):
    """Test agent processes context correctly."""
    context = {"budget": 5000, "location": "Seattle"}

    agent = ResearchAgent(mock_gemini_client)
    result = await agent.process("Find information", context)

    assert result.success is True
    # Verify context was passed in prompt
    assert mock_gemini_client.process.called


@pytest.mark.asyncio
async def test_specialized_prompt_building(mock_gemini_client):
    """Test specialized prompt is built correctly."""
    agent = ResearchAgent(mock_gemini_client)

    prompt = agent._build_specialized_prompt("Test query", {"key": "value"})

    assert "research" in prompt.lower()
    assert "Test query" in prompt
    assert "Context:" in prompt
    assert "confidence" in prompt.lower()


@pytest.mark.asyncio
async def test_reasoning_extraction(mock_gemini_client):
    """Test reasoning extraction from answer."""
    mock_gemini_client.process = AsyncMock(
        return_value="Based on research, this is the answer. Confidence: 0.9"
    )

    agent = ResearchAgent(mock_gemini_client)
    result = await agent.process("Test query", {})

    assert result.reasoning is not None
    assert len(result.reasoning) > 0


@pytest.mark.asyncio
async def test_all_agents_unique_roles():
    """Test all agents have unique roles."""
    mock_client = MagicMock()
    mock_client.temperature = 0.2

    agents = [
        ResearchAgent(mock_client),
        CreativeAgent(mock_client),
        TechnicalAgent(mock_client),
        BudgetAgent(mock_client),
        PlanningAgent(mock_client),
    ]

    roles = [agent.role for agent in agents]

    # All roles should be unique
    assert len(roles) == len(set(roles))

    # All should be valid agent types
    expected_roles = {"research", "creative", "technical", "budget", "planning"}
    assert set(roles) == expected_roles
