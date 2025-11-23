import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from max_os.agents.base import AgentRequest
from max_os.core.planner import Intent, IntentPlanner
from max_os.core.registry import AGENT_REGISTRY, AgentRegistry
from max_os.learning.context_engine import ContextAwarenessEngine
from max_os.learning.personality import UserPersonalityModel

logger = structlog.get_logger("max_os.learning.prediction")


@dataclass
class PredictionRecord:
    """Tracks lifecycle of a predicted intent."""

    intent: str
    task: str
    confidence: float
    timestamp: datetime
    status: str = "pending"  # pending|hit|miss|proactive
    proactive: bool = False


class PredictiveAgentSpawner:
    """
    Continuously predicts user needs and spawns agents proactively.
    """

    def __init__(
        self,
        personality: UserPersonalityModel,
        context_engine: ContextAwarenessEngine | None,
        planner: IntentPlanner | None = None,
        registry: AgentRegistry | None = None,
        prediction_ttl_seconds: int = 900,
        history_limit: int = 200,
    ):
        self.personality = personality
        self.context_engine = context_engine
        self.prediction_interval = 60  # seconds
        self.planner = planner or IntentPlanner()
        self.registry = registry or AGENT_REGISTRY
        self.prediction_history: deque[PredictionRecord] = deque(maxlen=history_limit)
        self.prediction_stats = {
            "total": 0,
            "hits": 0,
            "misses": 0,
        }
        self.prediction_ttl = timedelta(seconds=prediction_ttl_seconds)

    async def continuous_prediction_loop(self):
        """
        The main loop for continuous prediction.
        """
        if not self.context_engine:
            logger.warning("Context engine missing; skipping predictive loop.")
            return

        while True:
            try:
                # 1. Gather context
                context = await self.context_engine.gather_all_signals()

                # 2. Get predictions
                predictions = self.personality.predict_next_need(context)

                # 3. Spawn agents for high-confidence predictions
                await self.spawn_agents(predictions, context)

            except Exception as e:
                logger.error("Error in prediction loop", exc_info=e)

            await asyncio.sleep(self.prediction_interval)

    async def spawn_agents(self, predictions: list[dict[str, Any]], context: dict[str, Any] | None):
        """
        Spawns agents based on predictions.
        """
        if not predictions or context is None:
            return

        self._expire_predictions()

        for prediction in predictions:
            confidence = prediction.get("confidence", 0.0)
            if confidence <= 0.8:
                continue

            intent = self._plan_prediction(prediction, context)
            if not intent:
                continue

            record = self._record_prediction(intent, prediction)

            request_context = {
                "prediction_confidence": confidence,
                "prediction_reason": prediction.get("reason"),
                "prediction_type": prediction.get("type"),
                "signals": context,
            }
            request = AgentRequest(
                intent=intent.name,
                text=prediction.get("task", intent.summary or "predicted task"),
                context=request_context,
            )

            handled = False
            for agent in self.registry.get_all().values():
                try:
                    if agent.can_handle(request):
                        # Log the proactive action with full reasoning
                        agent_name = getattr(agent, "name", "unknown")
                        logger.info(
                            "proactive_action_dispatched",
                            agent=agent_name,
                            prediction_confidence=confidence,
                            predicted_need=prediction.get("task"),
                        )
                        await agent.handle(request)
                        self._mark_prediction_hit(record, proactive=True)
                        handled = True
                        break
                except Exception as exc:
                    agent_name = getattr(agent, "name", "unknown")
                    logger.exception(
                        "agent_failed_proactive_request",
                        agent=agent_name,
                        exc_info=exc,
                    )

            if not handled:
                logger.debug("No agent accepted proactive intent %s", intent.name)

    def record_user_intent(self, intent_name: str) -> None:
        """Record when the user manually triggers an intent to gauge accuracy."""
        if not intent_name:
            return

        self._expire_predictions()

        for record in self.prediction_history:
            if record.status == "pending" and record.intent == intent_name:
                self._mark_prediction_hit(record, proactive=False)
                return

    def get_prediction_metrics(self) -> dict[str, float]:
        """Expose simple accuracy metrics for observability."""
        total = self.prediction_stats["total"]
        accuracy = (
            self.prediction_stats["hits"] / total if total else 0.0
        )
        return {
            "total_predictions": total,
            "hits": self.prediction_stats["hits"],
            "misses": self.prediction_stats["misses"],
            "accuracy": round(accuracy, 3),
        }

    def _plan_prediction(self, prediction: dict[str, Any], context: dict[str, Any]) -> Intent | None:
        """Convert a predicted task into a structured Intent using the shared planner."""
        task = prediction.get("task")
        if not task:
            return None

        try:
            simple_context = {
                k: str(v)
                for k, v in context.items()
                if isinstance(v, (str, int, float, bool))
            }
            return self.planner.plan(task, simple_context)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Failed to plan prediction task '%s'", task, exc_info=exc)
            return None

    def _record_prediction(self, intent: Intent, prediction: dict[str, Any]) -> PredictionRecord:
        record = PredictionRecord(
            intent=intent.name,
            task=prediction.get("task", intent.summary or intent.name),
            confidence=prediction.get("confidence", 0.0),
            timestamp=datetime.now(UTC),
        )
        self.prediction_history.append(record)
        self.prediction_stats["total"] += 1
        return record

    def _mark_prediction_hit(self, record: PredictionRecord, proactive: bool) -> None:
        if record.status != "pending":
            return
        record.status = "proactive" if proactive else "hit"
        record.proactive = proactive
        self.prediction_stats["hits"] += 1

    def _expire_predictions(self) -> None:
        if not self.prediction_history:
            return
        cutoff = datetime.now(UTC) - self.prediction_ttl
        for record in self.prediction_history:
            if record.status == "pending" and record.timestamp < cutoff:
                record.status = "miss"
                self.prediction_stats["misses"] += 1
