"""
System Reflexes.
Zero-latency actions that bypass the LLM.
Checks for exact keyword matches (or simple regex) and executes immediately.
"""

import subprocess
from typing import Dict, Callable, Optional
import structlog

logger = structlog.get_logger("max_os.reflex")

class ReflexEngine:
    def __init__(self):
        self.reflexes: Dict[str, Callable[[], None]] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register core survival reflexes."""
        self.register("stop", self._stop_media)
        self.register("silence", self._stop_media)
        self.register("shut up", self._stop_media)
        
        self.register("lock", self._lock_screen)
        
        # self.register("freeze", self._freeze_system) # Risky, disabled for now

    def register(self, keyword: str, action: Callable[[], None]):
        self.reflexes[keyword.lower()] = action

    def check_and_trigger(self, text: str) -> bool:
        """
        Checks if text contains a reflex keyword.
        Returns True if a reflex was triggered (and thus we should stop processing).
        """
        text = text.lower().strip()
        
        # exact match or starts with for safety
        # in reality, we might want "stop music" to trigger "stop"
        for key, action in self.reflexes.items():
            if text == key or text.startswith(f"{key} "):
                logger.info(f"Reflex Triggered: {key}")
                try:
                    action()
                    return True
                except Exception as e:
                    logger.error(f"Reflex action failed: {key}", error=str(e))
                    return False
        return False

    def _stop_media(self):
        # Requires playerctl
        logger.info("REFLEX: Stopping Media")
        subprocess.run(["playerctl", "stop"], stderr=subprocess.DEVNULL)
        # Also mute fallback
        subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"], stderr=subprocess.DEVNULL)

    def _lock_screen(self):
        logger.info("REFLEX: Locking Screen")
        # Try gnome, standard interface
        subprocess.run(["xdg-screensaver", "lock"], stderr=subprocess.DEVNULL)
