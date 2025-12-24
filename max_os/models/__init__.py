"""Data models for MaxOS."""

from .multi_agent import (
    AgentDebateResponse,
    AgentResult,
    ConsensusCheck,
    DebateLog,
    DebateResult,
    ManagerReview,
)

__all__ = [
    "AgentResult",
    "ManagerReview",
    "AgentDebateResponse",
    "ConsensusCheck",
    "DebateLog",
    "DebateResult",
]
