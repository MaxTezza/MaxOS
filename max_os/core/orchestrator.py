"""Central orchestrator that parses intents and dispatches to agents."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List

from max_os.agents.base import AgentRequest, AgentResponse, BaseAgent
from max_os.agents.developer import DeveloperAgent
from max_os.agents.filesystem import FileSystemAgent
from max_os.agents.network import NetworkAgent
from max_os.agents.system import SystemAgent
from max_os.core.intent import Intent
from max_os.core.memory import ConversationMemory
from max_os.core.planner import IntentPlanner
from max_os.learning.personality import UserPersonalityModel, Interaction
from max_os.learning.prompt_filter import PromptOptimizationFilter
from max_os.utils.config import Settings, load_settings
from max_os.utils.logging import configure_logging


class AIOperatingSystem:
    """Registers all agents and dispatches user commands."""

    def __init__(self, settings: Settings | None = None, agents: List[BaseAgent] | None = None, enable_learning: bool = True) -> None:
        self.settings = settings or load_settings()
        configure_logging(self.settings)
        self.logger = logging.getLogger("max_os.orchestrator")
        self.planner = IntentPlanner()
        self.agents: List[BaseAgent] = agents or self._init_agents()
        self.memory = ConversationMemory(limit=50)

        # Learning system
        self.enable_learning = enable_learning
        if self.enable_learning:
            self.personality = UserPersonalityModel()
            self.prompt_filter = PromptOptimizationFilter(self.personality)
            self.logger.info("Learning system enabled", extra={
                "verbosity": self.personality.verbosity_preference,
                "technical_level": self.personality.technical_level
            })

    def _init_agents(self) -> List[BaseAgent]:
        agent_configs = self.settings.agents
        return [
            FileSystemAgent(agent_configs.get("filesystem")),
            DeveloperAgent(agent_configs.get("developer")),
            NetworkAgent(agent_configs.get("network")),
            SystemAgent(agent_configs.get("system")),
        ]

    def register_agent(self, agent: BaseAgent) -> None:
        self.agents.append(agent)

    def handle_text(self, text: str, context: Dict[str, object] | None = None) -> AgentResponse:
        context = context or {}
        self.memory.add_user(text)
        intent = self._plan_intent(text, context)
        self.logger.info("Planned intent", extra={"intent": intent.name, "slots": intent.to_context()})

        # Add last action to context for pattern detection
        recent_history = self.memory.history[-2:] if len(self.memory.history) >= 2 else []
        if recent_history and recent_history[0].role == "user":
            context['last_action'] = recent_history[0].content

        request = AgentRequest(intent=intent.name, text=text, context=context)

        for agent in self.agents:
            if agent.can_handle(request):
                response = agent.handle(request)
                if response.payload is None:
                    response.payload = {}
                response.payload.setdefault("intent", intent.name)
                response.payload.setdefault("slots", intent.to_context())
                response.payload.setdefault("summary", intent.summary)

                # Apply learning and optimization
                if self.enable_learning:
                    response = self._apply_learning(text, response, context, agent.name)

                self.memory.add_agent(response)
                self.logger.info(
                    "Agent handled request",
                    extra={"agent": response.agent, "status": response.status, "intent": intent.name},
                )
                return response

        fallback = AgentResponse(
            agent="orchestrator",
            status="unhandled",
            message="No registered agent accepted this request.",
            payload={"intent": intent.name, "text": text, "summary": intent.summary},
        )

        if self.enable_learning:
            fallback = self._apply_learning(text, fallback, context, "orchestrator")

        return fallback

    def _apply_learning(self, user_input: str, response: AgentResponse, context: Dict, agent_name: str) -> AgentResponse:
        """Apply personality learning and response optimization."""
        # Estimate technical complexity
        domain = context.get('domain', 'general')
        technical_complexity = self.prompt_filter.estimate_technical_complexity(
            response.message,
            domain
        )

        # Record interaction for learning
        interaction = Interaction(
            timestamp=datetime.now(),
            user_input=user_input,
            agent=agent_name,
            response_length=len(response.message),
            technical_complexity=technical_complexity,
            success=(response.status == "success"),
            context={'domain': domain},
            user_reaction=None  # Will be updated based on future interactions
        )

        # Learn from interaction
        self.personality.observe(interaction)

        # Optimize response
        optimized = self.prompt_filter.optimize_response(response, context)

        # Add predictive suggestions if available
        predictions = self.personality.predict_next_need(context)
        if predictions:
            optimized = self.prompt_filter.add_predictive_suggestions(
                optimized,
                predictions
            )

        return optimized

    def _plan_intent(self, text: str, context: Dict[str, object]) -> Intent:
        return self.planner.plan(text, {k: str(v) for k, v in context.items()})
