from __future__ import annotations

from typing import Any

import structlog

from max_os.core.entities import EntityExtractor
from max_os.core.intent import Intent
from max_os.core.planner import IntentPlanner
from max_os.core.prompts import build_llm_prompt
from max_os.utils.llm_api import LLMAPI


class IntentClassifier:
    """
    Classifies user intent based on prompt and context, returning a structured Intent object.
    Designed as a swappable component for different classification strategies.
    
    Can use LLM-powered classification when available, with fallback to keyword rules.
    """

    def __init__(
        self,
        planner: IntentPlanner | None = None,
        llm_api: LLMAPI | None = None,
        fallback_to_rules: bool = True,
    ):
        self.planner = planner or IntentPlanner()
        self.llm_api = llm_api
        self.fallback_to_rules = fallback_to_rules
        self.entity_extractor = EntityExtractor()
        self.logger = structlog.get_logger("max_os.intent_classifier")

    async def classify(self, prompt: str, context: dict[str, Any]) -> Intent:
        """
        Classifies the user's intent given the raw prompt and current context.

        Args:
            prompt: The raw user input string.
            context: A dictionary containing the current system context (e.g., active app, git status).

        Returns:
            An Intent object representing the classified intent.
        """
        # Try LLM-powered classification first if available
        if self.llm_api and self.llm_api.is_available():
            try:
                intent = await self._classify_with_llm(prompt, context)
                if intent:
                    self.logger.info(
                        "LLM classification successful",
                        extra={
                            "intent": intent.name,
                            "confidence": intent.confidence,
                            "slots_count": len(intent.slots)
                        }
                    )
                    return intent
            except Exception as e:
                self.logger.warning(
                    "LLM classification failed, falling back to rules",
                    extra={"error": str(e)}
                )
        
        # Fallback to rule-based classification
        if self.fallback_to_rules:
            return await self._classify_with_rules(prompt, context)
        
        # If no fallback and LLM failed, return low-confidence general intent
        return Intent(
            name="system.general",
            confidence=0.2,
            slots=[],
            summary="Unable to classify intent"
        )

    async def _classify_with_llm(self, prompt: str, context: dict[str, Any]) -> Intent | None:
        """
        Use LLM API to classify intent and extract entities.
        
        Args:
            prompt: User input text
            context: Current system context
            
        Returns:
            Intent object or None if classification fails
        """
        # Build the LLM prompt with system message and few-shot examples
        llm_prompt = build_llm_prompt(prompt, context)
        
        # Call LLM API
        try:
            response = await self.llm_api.generate_text(llm_prompt)
            self.logger.debug("LLM response received", extra={"response_length": len(response)})
            
            # Parse response into Intent
            intent = self.entity_extractor.extract_intent_from_llm(response)
            if intent:
                return intent
            else:
                self.logger.warning("Failed to parse LLM response into Intent")
                return None
                
        except Exception as e:
            self.logger.error("LLM API call failed", extra={"error": str(e)})
            raise

    async def _classify_with_rules(self, prompt: str, context: dict[str, Any]) -> Intent:
        """
        Use keyword rules for intent classification (original behavior).
        
        Args:
            prompt: User input text
            context: Current system context
            
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
