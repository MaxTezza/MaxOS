"""Central orchestrator that parses intents and dispatches to agents."""

from __future__ import annotations

import asyncio
from datetime import datetime

import structlog

from max_os.agents import (
    AGENT_REGISTRY,
    AgentEvolverAgent,
    DeveloperAgent,
    FileSystemAgent,
    KnowledgeAgent,
    NetworkAgent,
    SystemAgent,
)
from max_os.agents.base import AgentRequest, AgentResponse, BaseAgent
from max_os.core.intent import Intent
from max_os.core.intent_classifier import IntentClassifier
from max_os.core.memory import ConversationMemory
from max_os.core.planner import IntentPlanner
from max_os.learning.context_engine import ContextAwarenessEngine
from max_os.learning.personality import Interaction, UserPersonalityModel
from max_os.learning.prediction import PredictiveAgentSpawner
from max_os.learning.prompt_filter import PromptOptimizationFilter
from max_os.learning.realtime_engine import RealTimeLearningEngine
from max_os.utils.config import Settings, load_settings
from max_os.utils.logging import configure_logging


class AIOperatingSystem:
    """Registers all agents and dispatches user commands."""

    def __init__(
        self,
        settings: Settings | None = None,
        agents: list[BaseAgent] | None = None,
        enable_learning: bool = True,
        auto_start_loops: bool = False,
    ) -> None:
        self.settings = settings or load_settings()
        configure_logging(self.settings)
        self.logger = structlog.get_logger("max_os.orchestrator")
        self.planner = IntentPlanner()
        self.intent_classifier = IntentClassifier(self.planner, self.settings)  # Pass settings
        self.agents: list[BaseAgent] = agents or self._init_agents()
        self.memory = ConversationMemory(limit=50, settings=self.settings)
        self.last_context: dict[str, object] | None = None
        self._learning_tasks = []

        # Multi-agent orchestrator (optional)
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
                self.logger.info("Multi-agent orchestrator enabled")
            except Exception as e:
                self.logger.warning("Failed to initialize multi-agent orchestrator", error=str(e))

        # Learning system
        self.enable_learning = enable_learning
        if self.enable_learning:
            self.personality = UserPersonalityModel()
            self.prompt_filter = PromptOptimizationFilter(self.personality)
            self.context_engine = ContextAwarenessEngine()
            self.prediction_spawner = PredictiveAgentSpawner(
                self.personality,
                self.context_engine,
                planner=self.planner,
                registry=AGENT_REGISTRY,
            )
            # Find the AgentEvolverAgent instance
            agent_evolver = next(
                (agent for agent in self.agents if isinstance(agent, AgentEvolverAgent)), None
            )
            self.realtime_learning_engine = RealTimeLearningEngine(self.personality, agent_evolver)
            if auto_start_loops:
                self.start_learning_loops()
            self.logger.info(
                "Learning system enabled",
                extra={
                    "verbosity": self.personality.verbosity_preference,
                    "technical_level": self.personality.technical_level,
                },
            )
        else:
            self.context_engine = None
            self.prediction_spawner = None
            self.realtime_learning_engine = None

    def start_learning_loops(self):
        """Start background learning loops. Must be called within an async context."""
        try:
            if self.prediction_spawner:
                task = asyncio.create_task(self.prediction_spawner.continuous_prediction_loop())
                self._learning_tasks.append(task)
            if self.realtime_learning_engine:
                task = asyncio.create_task(self.realtime_learning_engine.run())
                self._learning_tasks.append(task)
        except RuntimeError:
            # No event loop running, tasks will need to be started manually
            self.logger.debug("No event loop running, learning loops not started")

    def shutdown(self):
        if self.context_engine:
            self.context_engine.shutdown()
        # The asyncio tasks for the learning loops will be cancelled
        # when the main event loop is closed.

    def _init_agents(self) -> list[BaseAgent]:
        agent_configs = self.settings.agents
        agents = [
            # AgentEvolver first to ensure it catches evolver-specific intents
            AgentEvolverAgent(),
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
        active_window = None  # Initialize active_window
        if self.enable_learning and self.context_engine and "signals" not in context:
            context["signals"] = await self._gather_context_signals()
            git_state = context["signals"].get("git", {})
            if git_state.get("dirty_count"):
                context.setdefault("git_status", "modified")
            else:
                context.setdefault("git_status", "clean")
            active_window = context["signals"].get("applications", {}).get("active_window")
            if active_window:
                context.setdefault("active_window", active_window)

        # Check if we should route to multi-agent system
        if (
            self.multi_agent
            and self.settings.multi_agent.get("route_complex_queries", True)
            and self._is_complex_query(text)
        ):
            try:
                result = await self.multi_agent.process_with_debate(
                    user_query=text, context=context, show_work=True
                )
                
                # Convert to AgentResponse
                response = AgentResponse(
                    agent="multi_agent",
                    status="success",
                    message=result.final_answer,
                    payload={
                        "agents_used": result.agents_used,
                        "confidence": result.confidence,
                        "work_logs": result.agent_work_logs,
                        "debate_log": result.debate_log,
                        "manager_review": result.manager_review,
                    },
                )
                
                self.memory.add_user(text)
                self.memory.add_agent(response)
                return response
                
            except Exception as e:
                self.logger.warning("Multi-agent processing failed, falling back", error=str(e))
                # Fall through to normal processing

        self.memory.add_user(text)
        intent = await self._plan_intent(text, context)
        self.last_context = context
        self.logger.info(
            "Planned intent", extra={"intent": intent.name, "slots": intent.to_context()}
        )

        if self.enable_learning and self.prediction_spawner:
            self.prediction_spawner.record_user_intent(intent.name)

        # Add last action to context for pattern detection
        recent_history = self.memory.history[-2:] if len(self.memory.history) >= 2 else []
        if recent_history and recent_history[0].role == "user":
            context["last_action"] = recent_history[0].content

        request = AgentRequest(intent=intent.name, text=text, context=context)

        for agent in self.agents:
            if agent.can_handle(request):
                response = await agent.handle(request)
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
                    extra={
                        "agent": response.agent,
                        "status": response.status,
                        "intent": intent.name,
                    },
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

    def _apply_learning(
        self, user_input: str, response: AgentResponse, context: dict, agent_name: str
    ) -> AgentResponse:
        """Apply personality learning and response optimization."""
        # Estimate technical complexity
        domain = context.get("domain", "general")
        technical_complexity = self.prompt_filter.estimate_technical_complexity(
            response.message, domain
        )

        # Record interaction for learning
        interaction = Interaction(
            timestamp=datetime.now(),
            user_input=user_input,
            agent=agent_name,
            response_length=len(response.message),
            technical_complexity=technical_complexity,
            success=(response.status == "success"),
            context={"domain": domain},
            user_reaction=None,  # Will be updated based on future interactions
        )

        # Learn from interaction
        if self.realtime_learning_engine:
            self.realtime_learning_engine.observe_interaction(interaction)

        # Optimize response
        optimized = self.prompt_filter.optimize_response(response, context)

        # Add predictive suggestions if available
        predictions = self.personality.predict_next_need(context)
        if predictions:
            optimized = self.prompt_filter.add_predictive_suggestions(optimized, predictions)

        return optimized

    async def _plan_intent(self, text: str, context: dict[str, object]) -> Intent:
        return await self.intent_classifier.classify(text, context)

    def get_last_context(self) -> dict[str, object]:
        return self.last_context or {}

    def get_learning_metrics(self) -> list[dict[str, float]]:
        if self.realtime_learning_engine:
            return self.realtime_learning_engine.get_recent_metrics()
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
        """Determine if query needs multi-agent processing.
        
        Args:
            text: User query
            
        Returns:
            True if query is complex
        """
        complex_keywords = [
            "plan",
            "analyze",
            "compare",
            "research",
            "should i",
            "what if",
            "help me decide",
            "evaluate",
            "assessment",
            "recommendation",
            "strategy",
            "proposal",
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in complex_keywords)

