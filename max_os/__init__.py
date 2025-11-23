"""MaxOS package exposing the orchestrator factory."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from .core.orchestrator import AIOperatingSystem

__all__ = ["AIOperatingSystem"]


def __getattr__(name: str):
    if name == "AIOperatingSystem":
        from .core.orchestrator import AIOperatingSystem

        return AIOperatingSystem
    raise AttributeError(f"module 'max_os' has no attribute {name!r}")
