from __future__ import annotations

from typing import Any

from max_os.core.intent import Intent
from max_os.core.planner import IntentPlanner  # Re-using existing planner for initial heuristics


class IntentClassifier:
    """
    Classifies user intent based on prompt and context, returning a structured Intent object.
    Designed as a swappable component for different classification strategies.
    """

    def __init__(self, planner: IntentPlanner | None = None):
        self.planner = planner or IntentPlanner() # Use existing planner for rule-based classification

    async def classify(self, prompt: str, context: dict[str, Any]) -> Intent:
        """
        Classifies the user's intent given the raw prompt and current context.

        Args:
            prompt: The raw user input string.
            context: A dictionary containing the current system context (e.g., active app, git status).

        Returns:
            An Intent object representing the classified intent.
        """
        # Heuristic 2.0: Operate on full context
        lowered_prompt = prompt.lower()

        # Example: Context-aware classification
        if context.get('git_status') == 'modified' and any(word in lowered_prompt for word in ['commit', 'push']):
            return Intent(name="dev.commit", confidence=0.9, summary="User wants to commit/push changes")
        
        # Fallback to existing rule-based planner
        # The planner's context parameter expects Dict[str, str], so convert if necessary
        str_context = {k: str(v) for k, v in context.items()}
        return self.planner.plan(prompt, str_context)

