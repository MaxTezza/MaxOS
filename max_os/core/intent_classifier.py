from __future__ import annotations

import asyncio
from typing import Any

import structlog

from max_os.core.entities import create_intent_from_llm_response, extract_and_validate_entities
from max_os.core.intent import Intent
from max_os.core.llm import LLMClient
from max_os.core.planner import IntentPlanner  # Re-using existing planner for initial heuristics
from max_os.core.prompts import build_user_prompt, get_system_prompt
from max_os.utils.config import Settings, load_settings


class IntentClassifier:
    """
    Classifies user intent based on prompt and context, returning a structured Intent object.
    Designed as a swappable component for different classification strategies.
    
    Uses LLM-powered classification when available, falls back to rule-based matching.
    """

    def __init__(
        self, 
        planner: IntentPlanner | None = None,
        settings: Settings | None = None,
        llm_client: LLMClient | None = None
    ):
        self.planner = (
            planner or IntentPlanner()
        )  # Use existing planner for rule-based classification
        self.settings = settings or load_settings()
        self.llm_client = llm_client or LLMClient(self.settings)
        self.logger = structlog.get_logger("max_os.intent_classifier")
        self.fallback_to_rules = self.settings.llm.get("fallback_to_rules", True)
        self.use_llm = self._should_use_llm()

    def _should_use_llm(self) -> bool:
        """Check if LLM classification should be used."""
        provider = self.settings.orchestrator.get("provider", "stub")
        if provider == "stub":
            return False
        
        # Check if we have API keys
        if provider == "anthropic":
            return self.llm_client._has_anthropic()
        elif provider == "openai":
            return self.llm_client._has_openai()
        
        return False

    async def classify(self, prompt: str, context: dict[str, Any]) -> Intent:
        """
        Classifies the user's intent given the raw prompt and current context.

        Args:
            prompt: The raw user input string.
            context: A dictionary containing the current system context (e.g., active app, git status).

        Returns:
            An Intent object representing the classified intent.
        """
        # Try LLM classification first if enabled
        if self.use_llm:
            try:
                intent = await self._classify_with_llm(prompt, context)
                self.logger.info(
                    "LLM classification successful",
                    intent=intent.name,
                    confidence=intent.confidence
                )
                return intent
            except asyncio.TimeoutError:
                self.logger.warning("LLM classification timed out, falling back to rules")
            except Exception as e:
                self.logger.warning(
                    "LLM classification failed, falling back to rules",
                    error=str(e)
                )
        
        # Fallback to rule-based classification
        return await self._classify_with_rules(prompt, context)
    
    async def _classify_with_llm(self, prompt: str, context: dict[str, Any]) -> Intent:
        """Classify intent using LLM.
        
        Args:
            prompt: User input text
            context: Context dictionary
            
        Returns:
            Intent object from LLM classification
            
        Raises:
            asyncio.TimeoutError: If LLM request times out
            Exception: If LLM classification fails
        """
        system_prompt = get_system_prompt()
        user_prompt = build_user_prompt(prompt, context)
        
        response_text = await self.llm_client.generate_async(system_prompt, user_prompt)
        
        intent = create_intent_from_llm_response(response_text)
        
        # Validate and enhance entities if needed
        if intent.slots:
            entities = {slot.name: slot.value for slot in intent.slots}
            whitelist = self.settings.agents.get("filesystem", {}).get("root_whitelist")
            validated_entities = extract_and_validate_entities(entities, whitelist)
            
            # Update slots with validated entities
            from max_os.core.intent import Slot
            intent.slots = [Slot(name=k, value=str(v)) for k, v in validated_entities.items()]
        
        return intent
    
    async def _classify_with_rules(self, prompt: str, context: dict[str, Any]) -> Intent:
        """Classify intent using rule-based matching.
        
        Args:
            prompt: User input text
            context: Context dictionary
            
        Returns:
            Intent object from rule-based classification
        """
        # Heuristic 2.0: Operate on full context
        lowered_prompt = prompt.lower()

        # Example: Context-aware classification
        if context.get("git_status") == "modified" and any(
            word in lowered_prompt for word in ["commit", "push"]
        ):
            return Intent(
                name="dev.commit", confidence=0.9, summary="User wants to commit/push changes"
            )

        # Fallback to existing rule-based planner
        # The planner's context parameter expects Dict[str, str], so convert if necessary
        str_context = {k: str(v) for k, v in context.items()}
        return self.planner.plan(prompt, str_context)
