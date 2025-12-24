"""Base class for specialized agents in multi-agent system."""

from __future__ import annotations

import re
from typing import Any

from max_os.core.gemini_client import GeminiClient
from max_os.models.multi_agent import AgentResult


class SpecializedAgent:
    """Base class for specialized agents."""

    def __init__(self, llm: GeminiClient, role: str, expertise: str):
        """Initialize specialized agent.
        
        Args:
            llm: GeminiClient instance
            role: Agent role (e.g., "research", "creative")
            expertise: Description of agent's expertise
        """
        self.llm = llm
        self.role = role
        self.expertise = expertise

    async def process(self, query: str, context: dict[str, Any] | None = None) -> AgentResult:
        """Process query with agent's specialization.
        
        Args:
            query: User query
            context: Additional context
            
        Returns:
            AgentResult with answer and metadata
        """
        context = context or {}
        specialized_prompt = self._build_specialized_prompt(query, context)

        try:
            answer = await self.llm.process(specialized_prompt)
            confidence = self._assess_confidence(answer)

            return AgentResult(
                agent_name=self.role,
                success=True,
                answer=answer,
                confidence=confidence,
                reasoning=self._extract_reasoning(answer),
            )

        except Exception as e:
            return AgentResult(
                agent_name=self.role,
                success=False,
                error=str(e),
                answer=None,
                confidence=0.0,
            )

    def _build_specialized_prompt(self, query: str, context: dict[str, Any]) -> str:
        """Build prompt with agent's specialization.
        
        Args:
            query: User query
            context: Additional context
            
        Returns:
            Specialized prompt
        """
        context_str = ""
        if context:
            context_str = f"\nContext: {context}"

        return f"""You are a specialized {self.role} agent.

Your expertise: {self.expertise}

Query: {query}{context_str}

Provide your specialized analysis:
- Focus on your area of expertise
- Provide evidence and reasoning
- Be specific and actionable
- State your confidence level at the end (0.0-1.0)

Your answer:
"""

    def _assess_confidence(self, answer: str) -> float:
        """Extract or estimate confidence from answer.
        
        Args:
            answer: Agent's answer
            
        Returns:
            Confidence score (0.0-1.0)
        """
        # Look for explicit confidence statements
        confidence_patterns = [
            r"confidence[:\s]+(\d+\.?\d*)%?",
            r"(\d+\.?\d*)%?\s+confidence",
            r"confidence[:\s]+(\d+\.?\d*)",
        ]

        for pattern in confidence_patterns:
            match = re.search(pattern, answer.lower())
            if match:
                value = float(match.group(1))
                # Convert percentage to decimal if needed
                if value > 1.0:
                    value = value / 100.0
                return min(max(value, 0.0), 1.0)

        # Heuristic based on hedging language
        hedging_words = ["maybe", "perhaps", "might", "could", "possibly", "uncertain"]
        hedging_count = sum(1 for word in hedging_words if word in answer.lower())

        if hedging_count >= 3:
            return 0.5
        elif hedging_count >= 1:
            return 0.7
        else:
            return 0.8

    def _extract_reasoning(self, answer: str) -> str:
        """Extract reasoning from answer.
        
        Args:
            answer: Agent's answer
            
        Returns:
            Extracted reasoning or full answer
        """
        # For now, return full answer
        # Could be enhanced to parse specific reasoning sections
        return answer
