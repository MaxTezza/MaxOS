"""
Twin Manager: The beating heart of MaxOS V2.
Manages two Gemini instances:
1. The Frontman (Type A): Fast, responsive, executes user commands.
2. The Observer (Type B): Slow, analytical, learns from the interaction.
"""

from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog
from max_os.core.llm import LLMClient
from max_os.utils.config import Settings
from max_os.core.knowledge.graph import GraphStore

logger = structlog.get_logger("max_os.twin_manager")

class TwinRole(Enum):
    FRONTMAN = "frontman"
    OBSERVER = "observer"

@dataclass
class TwinState:
    id: str  # "Twin-1" or "Twin-2"
    role: TwinRole
    personality_embedding: Dict[str, Any] = field(default_factory=dict)
    context_history: List[Dict[str, Any]] = field(default_factory=list)
    learning_rate: float = 1.0  # Starts high, decays over time

class TwinManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = LLMClient(settings)
        self.knowledge_graph = GraphStore()
        
        # Initialize Twins
        self.twin_1 = TwinState(id="Twin-1", role=TwinRole.FRONTMAN)
        self.twin_2 = TwinState(id="Twin-2", role=TwinRole.OBSERVER)
        
        # Metrics
        self.swaps_performed = 0
        self.last_swap_time = datetime.now()
        
        # Configuration
        self.swap_interval_seconds = 300  # Start fast (5 mins), will increase
        self.min_learning_confidence = 0.8

    @property
    def frontman(self) -> TwinState:
        return self.twin_1 if self.twin_1.role == TwinRole.FRONTMAN else self.twin_2

    @property
    def observer(self) -> TwinState:
        return self.twin_1 if self.twin_1.role == TwinRole.OBSERVER else self.twin_2

    async def process_user_request(self, text: str, context: Dict[str, Any]) -> str:
        """
        Main entry point. 
        1. Frontman handles the request immediately.
        2. Observer analyzes it in the background.
        3. Check for swap condition.
        """
        # 1. Frontman Execution
        response = await self._execute_frontman(text, context)
        
        # 2. Observer Analysis (Fire and forget, or await if critical)
        asyncio.create_task(self._run_observer_loop(text, context, response))
        
        # 3. Check Swap Logic
        await self._check_and_perform_swap()
        
        return response

    async def _execute_frontman(self, text: str, context: Dict[str, Any]) -> str:
        """High-speed execution using the Frontman's current personality."""
        logger.info(f"Frontman ({self.frontman.id}) processing request")
        
        # 1. Retrieve Knowledge (RAG)
        # Search for key terms in the user text to find relevant facts
        knowledge_context = self.knowledge_graph.get_context_string(text)
        
        # 2. Build Prompt
        system_prompt = self._build_system_prompt(self.frontman, knowledge_context)
        
        # 3. Call Gemini
        response = await self.llm.generate_async(
            system_prompt=system_prompt,
            user_prompt=text,
            max_tokens=1024
        )
        
        # Update Frontman's short-term context
        self.frontman.context_history.append({"role": "user", "content": text})
        self.frontman.context_history.append({"role": "assistant", "content": response})
        
        return response

    async def _run_observer_loop(self, text: str, context: Dict[str, Any], response: str):
        """Observer analyzes the interaction to update the personality map AND extract facts."""
        logger.info(f"Observer ({self.observer.id}) analyzing interaction")
        
        analysis_prompt = f"""
        ANALYZE THIS INTERACTION:
        User: {text}
        Assistant: {response}
        Context: {context}

        Task 1: Extract permanent facts about the user.
        Format: List of triples [Subject, Predicate, Object]
        Example: [["User", "likes", "Coffee"], ["User", "is_working_on", "MaxOS"]]

        Task 2: Extract user preferences/personality traits (JSON).
        
        Output JSON:
        {{
            "facts": [["S", "P", "O"], ...],
            "traits": {{...}}
        }}
        """
        
        try:
            # Call Gemini (Observer)
            analysis_text = await self.llm.generate_async(
                system_prompt="You are an expert behavioural analyst.",
                user_prompt=analysis_prompt,
                max_tokens=1000
            )
            
            # Simple parsing (assuming LLM complies with JSON request)
            # In production, use a robust JSON parser with retry
            import json
            start = analysis_text.find("{")
            end = analysis_text.rfind("}") + 1
            if start != -1 and end != -1:
                data = json.loads(analysis_text[start:end])
                
                # 1. Update Knowledge Graph
                facts = data.get("facts", [])
                for s, p, o in facts:
                    self.knowledge_graph.add_fact(s, p, o)
                
                # 2. Update Personality
                traits = data.get("traits", {})
                if traits:
                     self.observer.context_history.append({"role": "system", "content": f"Learned Traits: {traits}"})
                     # Merge into embedding dict (simplified)
                     self.observer.personality_embedding.update(traits)

        except Exception as e:
            logger.error("Observer analysis failed", error=str(e))

    async def _check_and_perform_swap(self):
        """Decides if Twins should swap roles."""
        time_since_swap = (datetime.now() - self.last_swap_time).total_seconds()
        
        # Early game: Swap often (every 5-10 interactions or X minutes)
        # Late game: Swap rarely
        
        if time_since_swap > self.swap_interval_seconds:
            await self._swap_roles()

    async def _swap_roles(self):
        """Performs the Hot Swap."""
        logger.info("♻️ INITIATING TWIN SWAP ♻️")
        
        # 1. Sync critical context (ensure new Frontman knows what just happened)
        # We merge the Observer's deep insights into the Frontman's active context
        
        # 2. Swap Enums
        old_frontman = self.frontman
        old_observer = self.observer
        
        old_frontman.role = TwinRole.OBSERVER
        old_observer.role = TwinRole.FRONTMAN
        
        self.swaps_performed += 1
        self.last_swap_time = datetime.now()
        
        # Decay logic: Make swaps less frequent over time
        self.swap_interval_seconds *= 1.1  # Increase gap by 10% each swap
        
        logger.info(f"Swap Complete. New Frontman: {self.frontman.id}. Next swap in {self.swap_interval_seconds:.0f}s")

    def _build_system_prompt(self, twin: TwinState, knowledge_context: str = "") -> str:
        """Constructs the system prompt based on likely learned traits."""
        base_prompt = "You are MaxOS, a highly advanced, hands-free AI operating system."
        
        if knowledge_context:
            base_prompt += f"\n\n{knowledge_context}"
        
        # Inject learned headers
        if twin.personality_embedding:
            base_prompt += f"\n\nLearned User Preferences:\n{twin.personality_embedding}"
            
        return base_prompt

    async def anticipate_needs(self, context: Dict[str, Any]) -> Optional[str]:
        """
        The Anticipation Engine.
        Checks current context (Time, App, Location) against learned patterns.
        Returns a proactive suggestion (text) or None.
        """
        # 1. Simple Heuristic Check (The "Hard-coded" Anticipation)
        # In the future, this will be vector search against history.
        
        current_hour = datetime.now().hour
        
        # Example Pattern: "Heavy Metal after Work"
        # Triggers: Time > 17:00, Weekday, User just arrived (mock signal)
        if 17 <= current_hour <= 19:
            # Check if we already suggested this today (to avoid spam)
            # pseudo-code: if not self.already_suggested("music_after_work"):
            return "It's been a long day. Shall I put on some heavy metal?"
            
        # Example Pattern: "Morning Briefing"
        if 8 <= current_hour <= 9:
             return "Good morning. Ready for your daily briefing?"
             
        return None
