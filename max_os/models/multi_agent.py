"""Data models for multi-agent orchestration system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentResult:
    """Result from a specialized agent's processing."""

    agent_name: str
    success: bool
    answer: Optional[str]
    confidence: float
    reasoning: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ManagerReview:
    """Manager's review of all agent results."""

    needs_debate: bool
    conflicts: list[str]
    synthesis: Optional[str]
    confidence: float


@dataclass
class AgentDebateResponse:
    """An agent's response during a debate round."""

    agent_name: str
    round: int
    response: str


@dataclass
class ConsensusCheck:
    """Result of checking if consensus has been reached."""

    reached: bool
    final_answer: Optional[str]
    reasoning: str


@dataclass
class DebateLog:
    """Complete log of a debate between agents."""

    rounds: list[list[AgentDebateResponse]]
    consensus_reached: bool
    consensus: str
    rounds_needed: int
    executive_decision: bool = False


@dataclass
class DebateResult:
    """Final result from multi-agent processing with debate."""

    final_answer: str
    agent_work_logs: Optional[list[AgentResult]]
    manager_review: ManagerReview
    debate_log: Optional[DebateLog]
    agents_used: list[str]
    confidence: float
