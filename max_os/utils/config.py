"""Minimal configuration loader for MaxOS."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml

DEFAULT_PATH = "config/settings.yaml"
SAMPLE_PATH = "config/settings.example.yaml"


@dataclass
class Settings:
    orchestrator: Dict[str, Any] = field(default_factory=dict)
    agents: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    llm: Dict[str, Any] = field(default_factory=dict)
    policy: Dict[str, Any] = field(default_factory=dict)
    logging: Dict[str, Any] = field(default_factory=dict)
    telemetry: Dict[str, Any] = field(default_factory=dict)


def load_settings(path: str | None = None) -> Settings:
    """Load YAML settings; fall back to the sample if needed."""

    candidate = path or os.environ.get("AI_OS_CONFIG", DEFAULT_PATH)
    chosen_path = Path(candidate)
    if not chosen_path.exists():
        chosen_path = Path(SAMPLE_PATH)
    with chosen_path.open("r", encoding="utf-8") as handle:
        data: Dict[str, Any] = yaml.safe_load(handle) or {}
    return Settings(**data)
