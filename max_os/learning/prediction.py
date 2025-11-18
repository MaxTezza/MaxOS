import asyncio
from typing import Any, Dict, List, Optional
import structlog
from max_os.core.registry import AGENT_REGISTRY, AgentRegistry
from max_os.core.planner import Intent, IntentPlanner
from max_os.learning.context_engine import ContextAwarenessEngine
from max_os.learning.personality import UserPersonalityModel
from max_os.agents.base import AgentRequest

logger = structlog.get_logger("max_os.learning.prediction")


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
    ):
        self.personality = personality
        self.context_engine = context_engine
        self.prediction_interval = 60  # seconds
        self.planner = planner or IntentPlanner()
        self.registry = registry or AGENT_REGISTRY

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

    async def spawn_agents(self, predictions: List[Dict[str, Any]], context: Dict[str, Any] | None):
        """
        Spawns agents based on predictions.
        """
        if not predictions or context is None:
            return

        for prediction in predictions:
            confidence = prediction.get("confidence", 0.0)
            if confidence <= 0.8:
                continue

            intent = self._plan_prediction(prediction, context)
            if not intent:
                continue

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

    def _plan_prediction(self, prediction: Dict[str, Any], context: Dict[str, Any]) -> Optional[Any]:
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
