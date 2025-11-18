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


class RejectingAgent:
    """Agent that never handles a request (used to keep predictions pending)."""

    name = "rejector"

    def can_handle(self, request):
        return False

    async def handle(self, request):
        raise RuntimeError("Should never be called")


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


@pytest.mark.asyncio
async def test_prediction_metrics_track_proactive_hits(tmp_path):
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

    metrics = spawner.get_prediction_metrics()
    assert metrics["total_predictions"] == 1
    assert metrics["hits"] == 1
    assert spawner.prediction_history[0].status == "proactive"


@pytest.mark.asyncio
async def test_prediction_matches_user_intents(tmp_path):
    personality = UserPersonalityModel(db_path=tmp_path / "personality.db")
    registry = AgentRegistry()
    registry.register(RejectingAgent())

    spawner = PredictiveAgentSpawner(
        personality=personality,
        context_engine=None,
        planner=IntentPlanner(),
        registry=registry,
    )

    prediction = {"task": "show system health", "confidence": 0.95}
    context = {"time_of_day": "09:00"}
    await spawner.spawn_agents([prediction], context)

    assert spawner.get_prediction_metrics()["hits"] == 0

    pending_intent = spawner.prediction_history[0].intent
    spawner.record_user_intent(pending_intent)

    metrics = spawner.get_prediction_metrics()
    assert metrics["hits"] == 1
    assert spawner.prediction_history[0].status == "hit"


@pytest.mark.asyncio
async def test_prediction_expiration_counts_as_miss(tmp_path):
    personality = UserPersonalityModel(db_path=tmp_path / "personality.db")
    registry = AgentRegistry()
    registry.register(RejectingAgent())

    spawner = PredictiveAgentSpawner(
        personality=personality,
        context_engine=None,
        planner=IntentPlanner(),
        registry=registry,
        prediction_ttl_seconds=1,
    )

    prediction = {"task": "show system health", "confidence": 0.95}
    context = {"time_of_day": "09:00"}
    await spawner.spawn_agents([prediction], context)

    await asyncio.sleep(1.1)
    spawner.record_user_intent("unmatched.intent")

    metrics = spawner.get_prediction_metrics()
    assert metrics["misses"] == 1
    assert spawner.prediction_history[0].status == "miss"
