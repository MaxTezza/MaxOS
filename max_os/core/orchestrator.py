"""Central orchestrator that parses intents and dispatches to agents."""
from __future__ import annotations

import logging
from typing import Dict, List

from max_os.agents.base import AgentRequest, AgentResponse, BaseAgent
from max_os.agents.developer import DeveloperAgent
from max_os.agents.filesystem import FileSystemAgent
from max_os.agents.network import NetworkAgent
from max_os.agents.system import SystemAgent
from max_os.core.intent import Intent
from max_os.core.memory import ConversationMemory
from max_os.core.planner import IntentPlanner
from max_os.utils.config import Settings, load_settings
from max_os.utils.logging import configure_logging


class AIOperatingSystem:
    """Registers all agents and dispatches user commands."""

    def __init__(self, settings: Settings | None = None, agents: List[BaseAgent] | None = None) -> None:
        self.settings = settings or load_settings()
        configure_logging(self.settings)
        self.logger = logging.getLogger("max_os.orchestrator")
        self.planner = IntentPlanner()
        self.agents: List[BaseAgent] = agents or self._init_agents()
        self.memory = ConversationMemory(limit=50)

    def _init_agents(self) -> List[BaseAgent]:
        agent_configs = self.settings.agents
        return [
            FileSystemAgent(agent_configs.get("filesystem")),
            DeveloperAgent(agent_configs.get("developer")),
            SystemAgent(agent_configs.get("system")),
            NetworkAgent(agent_configs.get("network")),
        ]

    def register_agent(self, agent: BaseAgent) -> None:
        self.agents.append(agent)

    def handle_text(self, text: str, context: Dict[str, object] | None = None) -> AgentResponse:
        context = context or {}
        self.memory.add_user(text)
        intent = self._plan_intent(text, context)
        self.logger.info("Planned intent", extra={"intent": intent.name, "slots": intent.to_context()})
        request = AgentRequest(intent=intent.name, text=text, context=context)

        for agent in self.agents:
            if agent.can_handle(request):
                response = agent.handle(request)
                if response.payload is None:
                    response.payload = {}
                response.payload.setdefault("intent", intent.name)
                response.payload.setdefault("slots", intent.to_context())
                response.payload.setdefault("summary", intent.summary)
                self.memory.add_agent(response)
                self.logger.info(
                    "Agent handled request",
                    extra={"agent": response.agent, "status": response.status, "intent": intent.name},
                )
                return response

        return AgentResponse(
            agent="orchestrator",
            status="unhandled",
            message="No registered agent accepted this request.",
            payload={"intent": intent.name, "text": text, "summary": intent.summary},
        )

    def _plan_intent(self, text: str, context: Dict[str, object]) -> Intent:
        return self.planner.plan(text, {k: str(v) for k, v in context.items()})
