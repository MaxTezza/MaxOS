"""Common data structures and base classes for MaxOS agents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol


@dataclass
class AgentRequest:
    """Normalized request passed into an agent."""

    intent: str
    text: str
    context: Dict[str, Any]


@dataclass
class AgentResponse:
    """Structured response returned by an agent."""

    agent: str
    status: str
    message: str
    payload: Dict[str, Any] | None = None


class BaseAgent(Protocol):
    """Interface implemented by every specialized agent."""

    name: str
    description: str
    capabilities: List[str]

    def can_handle(self, request: AgentRequest) -> bool:
        """Return True if this agent can handle the incoming request."""

    def handle(self, request: AgentRequest) -> AgentResponse:
        """Execute the request and return a structured response."""
