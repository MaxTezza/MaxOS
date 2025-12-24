"""Context manager for Gemini's 2M token window."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog


@dataclass
class UserContext:
    """User context for persistent storage."""

    user_id: str
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    user_profile: dict[str, Any] = field(default_factory=dict)
    pantry_items: list[str] = field(default_factory=list)
    music_history: list[str] = field(default_factory=list)
    routines: dict[str, Any] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "conversation_history": self.conversation_history,
            "user_profile": self.user_profile,
            "pantry_items": self.pantry_items,
            "music_history": self.music_history,
            "routines": self.routines,
            "preferences": self.preferences,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserContext:
        """Create from dictionary."""
        return cls(**data)


class ContextManager:
    """Manages persistent context using Gemini's 2M token window."""

    def __init__(
        self,
        user_id: str,
        storage_path: str | Path | None = None,
        max_history: int = 1000,
    ) -> None:
        """Initialize context manager.

        Args:
            user_id: User identifier
            storage_path: Path to store context (defaults to ~/.maxos/context/)
            max_history: Maximum conversation history entries to keep
        """
        self.user_id = user_id
        self.max_history = max_history
        self.logger = structlog.get_logger("max_os.context_manager")

        # Setup storage
        if storage_path is None:
            storage_path = Path.home() / ".maxos" / "context"
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.context_file = self.storage_path / f"{user_id}.json"

        # Load or initialize context
        self.context = self._load_context()

    def _load_context(self) -> UserContext:
        """Load context from disk."""
        if self.context_file.exists():
            try:
                with self.context_file.open("r") as f:
                    data = json.load(f)
                self.logger.info("Loaded user context", user_id=self.user_id)
                return UserContext.from_dict(data)
            except Exception as e:
                self.logger.error("Failed to load context", error=str(e))

        # Return new context if loading failed
        return UserContext(user_id=self.user_id)

    def save_context(self) -> None:
        """Save context to disk."""
        try:
            self.context.last_updated = datetime.now().isoformat()
            with self.context_file.open("w") as f:
                json.dump(self.context.to_dict(), f, indent=2)
            self.logger.info("Saved user context", user_id=self.user_id)
        except Exception as e:
            self.logger.error("Failed to save context", error=str(e))

    def add_conversation(self, role: str, content: str) -> None:
        """Add a conversation message to history.

        Args:
            role: Message role (user/assistant/system)
            content: Message content
        """
        self.context.conversation_history.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Trim history if needed
        if len(self.context.conversation_history) > self.max_history:
            self.context.conversation_history = self.context.conversation_history[
                -self.max_history :
            ]

        self.save_context()

    def get_conversation_history(self, limit: int | None = None) -> list[dict[str, str]]:
        """Get conversation history.

        Args:
            limit: Optional limit on number of messages to return

        Returns:
            List of conversation messages
        """
        history = self.context.conversation_history
        if limit:
            history = history[-limit:]
        return history

    def clear_conversation_history(self) -> None:
        """Clear conversation history."""
        self.context.conversation_history = []
        self.save_context()

    def update_user_profile(self, profile_data: dict[str, Any]) -> None:
        """Update user profile.

        Args:
            profile_data: Profile data to update
        """
        self.context.user_profile.update(profile_data)
        self.save_context()

    def get_user_profile(self) -> dict[str, Any]:
        """Get user profile."""
        return self.context.user_profile.copy()

    def update_pantry(self, items: list[str]) -> None:
        """Update pantry items.

        Args:
            items: List of pantry items
        """
        self.context.pantry_items = items
        self.save_context()

    def add_pantry_item(self, item: str) -> None:
        """Add item to pantry.

        Args:
            item: Item to add
        """
        if item not in self.context.pantry_items:
            self.context.pantry_items.append(item)
            self.save_context()

    def remove_pantry_item(self, item: str) -> None:
        """Remove item from pantry.

        Args:
            item: Item to remove
        """
        if item in self.context.pantry_items:
            self.context.pantry_items.remove(item)
            self.save_context()

    def get_pantry_items(self) -> list[str]:
        """Get pantry items."""
        return self.context.pantry_items.copy()

    def add_music_history(self, track: str) -> None:
        """Add track to music history.

        Args:
            track: Track name/info
        """
        self.context.music_history.append(track)
        # Keep only last 100 tracks
        if len(self.context.music_history) > 100:
            self.context.music_history = self.context.music_history[-100:]
        self.save_context()

    def get_music_history(self, limit: int = 20) -> list[str]:
        """Get music history.

        Args:
            limit: Number of recent tracks to return

        Returns:
            List of recent tracks
        """
        return self.context.music_history[-limit:]

    def update_routines(self, routines: dict[str, Any]) -> None:
        """Update user routines.

        Args:
            routines: Routine data
        """
        self.context.routines.update(routines)
        self.save_context()

    def get_routines(self) -> dict[str, Any]:
        """Get user routines."""
        return self.context.routines.copy()

    def update_preferences(self, preferences: dict[str, Any]) -> None:
        """Update user preferences.

        Args:
            preferences: Preference data
        """
        self.context.preferences.update(preferences)
        self.save_context()

    def get_preferences(self) -> dict[str, Any]:
        """Get user preferences."""
        return self.context.preferences.copy()

    def build_context_summary(self) -> str:
        """Build a summary of the current context for inclusion in prompts.

        Returns:
            Formatted context summary
        """
        summary_parts = []

        if self.context.user_profile:
            summary_parts.append(f"User Profile: {json.dumps(self.context.user_profile)}")

        if self.context.pantry_items:
            summary_parts.append(f"Pantry Items: {', '.join(self.context.pantry_items[:20])}")

        if self.context.music_history:
            recent_music = self.context.music_history[-5:]
            summary_parts.append(f"Recent Music: {', '.join(recent_music)}")

        if self.context.routines:
            summary_parts.append(f"Routines: {json.dumps(self.context.routines)}")

        if self.context.preferences:
            summary_parts.append(f"Preferences: {json.dumps(self.context.preferences)}")

        return "\n".join(summary_parts) if summary_parts else "No context available"

    def get_full_context(self) -> UserContext:
        """Get full context object."""
        return self.context
