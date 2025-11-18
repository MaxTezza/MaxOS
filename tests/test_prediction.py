import asyncio

import pytest

from max_os.agents.base import AgentResponse
from max_os.core.planner import IntentPlanner
from max_os.core.registry import AgentRegistry
from max_os.learning.personality import UserPersonalityModel
from max_os.learning.prediction import PredictiveAgentSpawner


class DummyAgent:
    name = "system"

    def __init__(self):
        self.handles = 0

    def can_handle(self, request):
        return request.intent.startswith("system.")

    async def handle(self, request):
        self.handles += 1
        return AgentResponse(
            agent=self.name,
            status="success",
            message="handled proactively",
            payload={"intent": request.intent},
        )


@pytest.mark.asyncio
async def test_predictive_spawner_routes_with_planner(tmp_path):
    personality = UserPersonalityModel(db_path=tmp_path / "personality.db")
    registry = AgentRegistry()
    agent = DummyAgent()
    registry.register(agent)

    spawner = PredictiveAgentSpawner(
        personality=personality,
        context_engine=None,
        planner=IntentPlanner(),
        registry=registry,
    )

    prediction = {"task": "show system health", "confidence": 0.95}
    context = {"time_of_day": "09:00"}

    await spawner.spawn_agents([prediction], context)

    assert agent.handles == 1
