"""Common data structures and base classes for MaxOS agents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class AgentRequest:
    """Normalized request passed into an agent."""

    intent: str
    text: str
    context: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "text": self.text,
            "context": self.context,
        }


@dataclass
class AgentResponse:
    """Structured response returned by an agent."""

    agent: str
    status: str
    message: str
    payload: dict[str, Any] | None = None


class BaseAgent(Protocol):
    """Interface implemented by every specialized agent."""

    name: str
    description: str
    capabilities: list[str]

    def can_handle(self, request: AgentRequest) -> bool:
        """Return True if this agent can handle the incoming request."""

    async def handle(self, request: AgentRequest) -> AgentResponse:
        """Execute the request and return a structured response."""
