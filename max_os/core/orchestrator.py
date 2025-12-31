"""Central orchestrator that parses intents and dispatches to agents."""

from __future__ import annotations

import asyncio
from datetime import datetime

import structlog

from max_os.agents import (
    AGENT_REGISTRY,
    AgentEvolverAgent,
    AppLauncherAgent,
    DeveloperAgent,
    FileSystemAgent,
    HomeAutomationAgent,
    KnowledgeAgent,
    MediaAgent,
    NetworkAgent,
    SystemAgent,
)
from max_os.agents.base import AgentRequest, AgentResponse, BaseAgent
from max_os.core.intent import Intent
from max_os.core.intent_classifier import IntentClassifier
from max_os.core.memory import ConversationMemory
from max_os.core.planner import IntentPlanner
from max_os.learning.context_engine import ContextAwarenessEngine
# Removed legacy personality/learning imports
from max_os.core.twin_manager import TwinManager
from max_os.utils.config import Settings, load_settings
from max_os.utils.logging import configure_logging


class AIOperatingSystem:
    """Registers all agents and dispatches user commands."""

    def __init__(
        self,
        settings: Settings | None = None,
        agents: list[BaseAgent] | None = None,
        auto_start_loops: bool = False,
    ) -> None:
        self.settings = settings or load_settings()
        configure_logging(self.settings)
        self.logger = structlog.get_logger("max_os.orchestrator")
        
        # V2: Initialize Twin Manager
        self.twin_manager = TwinManager(self.settings)
        
        self.planner = IntentPlanner()
        self.intent_classifier = IntentClassifier(self.planner, self.settings)
        self.agents: list[BaseAgent] = agents or self._init_agents()
        self.memory = ConversationMemory(limit=50, settings=self.settings)
        self.last_context: dict[str, object] | None = None
        self._learning_tasks = []

        # Multi-agent orchestrator (Google Gemini)
        self.multi_agent = None
        if self.settings.multi_agent.get("enabled", False):
            try:
                from max_os.core.multi_agent_orchestrator import MultiAgentOrchestrator
                
                # Build config for multi-agent system
                ma_config = {
                    "google_api_key": self.settings.multi_agent.get("google_api_key") 
                                     or self.settings.llm.get("google_api_key"),
                    "max_debate_rounds": self.settings.multi_agent.get("max_debate_rounds", 3),
                    "consensus_threshold": self.settings.multi_agent.get("consensus_threshold", 0.8),
                }
                self.multi_agent = MultiAgentOrchestrator(ma_config)
                self.logger.info("Multi-agent orchestrator enabled (Gemini)")
            except Exception as e:
                self.logger.warning("Failed to initialize multi-agent orchestrator", error=str(e))

        # Context Engine (Retained for V2 context awareness)
        self.context_engine = ContextAwarenessEngine()
        
        # Removed legacy personality/prediction engines
        self.personality = None
        self.prompt_filter = None
        self.prediction_spawner = None
        self.realtime_learning_engine = None

    def start_learning_loops(self):
        """Start background loops. Must be called within an async context."""
        # V2: Will start Twin B (Observer) loop here
        pass

    def shutdown(self):
        if self.context_engine:
            self.context_engine.shutdown()

    def _init_agents(self) -> list[BaseAgent]:
        agent_configs = self.settings.agents
        agents = [
            # AgentEvolver first to ensure it catches evolver-specific intents
            AgentEvolverAgent(),
            AppLauncherAgent(agent_configs.get("app_launcher")),
            MediaAgent(agent_configs.get("media")),
            HomeAutomationAgent(agent_configs.get("home_automation")),
            KnowledgeAgent(agent_configs.get("knowledge")),
            FileSystemAgent(agent_configs.get("filesystem")),
            DeveloperAgent(agent_configs.get("developer")),
            NetworkAgent(agent_configs.get("network")),
            # SystemAgent last as it has broad keyword matching
            SystemAgent(agent_configs.get("system")),
        ]
        for agent in agents:
            AGENT_REGISTRY.register(agent)
        return agents

    def register_agent(self, agent: BaseAgent) -> None:
        self.agents.append(agent)

    async def handle_text(
        self, text: str, context: dict[str, object] | None = None
    ) -> AgentResponse:
        context = context or {}
        
        # V2: Twin Manager handles the interaction
        # The Twin (Frontman) decides what to say/do.
        # For now, we still use the Intent Planner for *actions*, 
        # but the Twin provides the *voice/personality*.
        
        # 1. Plan Intent (Action)
        intent = await self._plan_intent(text, context)
        self.logger.info("Planned intent", extra={"intent": intent.name})

        # 2. Execute Action (via Agents)
        request = AgentRequest(intent=intent.name, text=text, context=context)
        agent_response = None
        
        for agent in self.agents:
            if agent.can_handle(request):
                agent_response = await agent.handle(request)
                break
        
        if not agent_response:
             agent_response = AgentResponse(
                agent="orchestrator",
                status="unhandled",
                message="I'm not sure how to help with that yet.",
                payload={}
            )

        # 3. Twin Interaction (Voice/Personality Layer)
        # The Twin validates the action or explains it to the user
        twin_response_text = await self.twin_manager.process_user_request(
            text, 
            {
                **context, 
                "intent": intent.name, 
                "agent_outcome": agent_response.message
            }
        )
        
        # Override the technical agent message with the Twin's personality-infused message
        agent_response.message = twin_response_text
        
        self.memory.add_user(text)
        self.memory.add_agent(agent_response)
        
        return agent_response

    async def check_for_proactive_events(self, context: dict[str, object] | None = None) -> str | None:
        """
        Called periodically by the main loop.
        Asks the Twin Manager if it wants to say something proactively.
        """
        context = context or {}
        suggestion = await self.twin_manager.anticipate_needs(context)
        if suggestion:
            self.logger.info("Proactive suggestion triggered", suggestion=suggestion)
            return suggestion
        return None

    async def _plan_intent(self, text: str, context: dict[str, object]) -> Intent:
        return await self.intent_classifier.classify(text, context)

    def get_last_context(self) -> dict[str, object]:
        return self.last_context or {}

    def get_learning_metrics(self) -> list[dict[str, float]]:
        return []

    async def _gather_context_signals(self) -> dict[str, object]:
        if not self.context_engine:
            return {}

        try:
            return await self.context_engine.gather_all_signals(timeout=5)
        except asyncio.TimeoutError:
            self.logger.warning("Context signal collection timed out")
            return {}
        except Exception:
            self.logger.exception("Failed to gather context signals")
            return {}

    def _is_complex_query(self, text: str) -> bool:
        """Determine if query needs multi-agent processing."""
        complex_keywords = [
            "plan", "analyze", "compare", "research", "should i",
            "what if", "help me decide", "evaluate", "assessment",
            "recommendation", "strategy", "proposal",
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in complex_keywords)

