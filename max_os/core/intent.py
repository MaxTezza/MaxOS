"""Intent schema shared between planner, orchestrator, and agents."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Slot(BaseModel):
    name: str
    value: str


class Intent(BaseModel):
    name: str = Field(..., description="Machine-readable intent id, e.g. file.archive")
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    slots: List[Slot] = Field(default_factory=list)
    summary: Optional[str] = None

    def to_context(self) -> Dict[str, str]:
        return {slot.name: slot.value for slot in self.slots}
