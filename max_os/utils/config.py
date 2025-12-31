"""Dynamic configuration manager for MaxOS."""

from __future__ import annotations

import os
import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import structlog

load_dotenv()
logger = structlog.get_logger("max_os.config")

DEFAULT_PATH = "config/settings.yaml"
SAMPLE_PATH = "config/settings.example.yaml"

@dataclass
class Settings:
    orchestrator: dict[str, Any] = field(default_factory=dict)
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    llm: dict[str, Any] = field(default_factory=dict)
    policy: dict[str, Any] = field(default_factory=dict)
    logging: dict[str, Any] = field(default_factory=dict)
    telemetry: dict[str, Any] = field(default_factory=dict)
    multi_agent: dict[str, Any] = field(default_factory=dict)
    
    # Phase 6: Accessibility & Control
    accessibility: dict[str, Any] = field(default_factory=lambda: {
        "voice_speed": 1.0,
        "voice_volume": 1.0,
        "gui_scale": 100,
        "high_contrast": False
    })

    _file_path: str = field(default=DEFAULT_PATH, repr=False)

    def update(self, key_path: str, value: Any):
        """Updates a setting by dot-notation key (e.g. 'accessibility.voice_speed')."""
        keys = key_path.split(".")
        target = self.__dict__
        
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        
        target[keys[-1]] = value
        logger.info(f"Setting updated: {key_path} = {value}")
        self.save()

    def save(self):
        """Persists current state to YAML."""
        data = asdict(self)
        # Remove internal fields
        if "_file_path" in data: del data["_file_path"]
        
        try:
            with open(self._file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False)
            logger.info("Settings saved to disk.")
        except Exception as e:
            logger.error("Failed to save settings", error=str(e))

def load_settings(path: str | None = None) -> Settings:
    """Load YAML settings with read/write capability."""
    candidate = path or os.environ.get("AI_OS_CONFIG", DEFAULT_PATH)
    chosen_path = Path(candidate)
    
    if not chosen_path.exists():
        # If real settings don't exist, try to copy sample or just load sample
        sample = Path(SAMPLE_PATH)
        if sample.exists():
             import shutil
             shutil.copy(sample, chosen_path)
             logger.info(f"Created {chosen_path} from sample.")
        else:
             logger.warning("No settings file found. Using defaults.")
             return Settings(_file_path=candidate)

    with chosen_path.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle) or {}
    
    # Inject file path for saving later
    data["_file_path"] = str(chosen_path)
    
    return Settings(**data)
