"""Intent schema shared between planner, orchestrator, and agents."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Slot(BaseModel):
    name: str
    value: str


class Intent(BaseModel):
    name: str = Field(..., description="Machine-readable intent id, e.g. file.archive")
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    slots: list[Slot] = Field(default_factory=list)
    summary: str | None = None

    def to_context(self) -> dict[str, str]:
        return {slot.name: slot.value for slot in self.slots}
