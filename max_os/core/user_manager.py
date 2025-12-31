"""
MaxOS User Manager.
Handles multi-user profiles, preferences, and session state.
"""

import os
import json
import structlog
from typing import Dict, Any, Optional
from pathlib import Path

logger = structlog.get_logger("max_os.users")

class UserProfile:
    """Individual user profile data."""
    def __init__(self, username: str, user_dir: Path):
        self.username = username
        self.user_dir = user_dir
        self.settings_file = user_dir / "settings.json"
        self.settings: Dict[str, Any] = self._load_settings()
        
    def _load_settings(self) -> Dict[str, Any]:
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self):
        """Persists user settings to disk."""
        self.user_dir.mkdir(parents=True, exist_ok=True)
        with open(self.settings_file, "w") as f:
            json.dump(self.settings, f, indent=4)

class UserManager:
    """Manages global users and their active sessions."""
    
    def __init__(self, base_dir: str = "~/.maxos/users"):
        self.base_dir = Path(os.path.expanduser(base_dir))
        self.users: Dict[str, UserProfile] = {}
        self.active_user: Optional[UserProfile] = None
        self._load_users()

    def _load_users(self):
        """Discovers existing users on disk."""
        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True, exist_ok=True)
            return

        for user_path in self.base_dir.iterdir():
            if user_path.is_dir():
                username = user_path.name
                self.users[username] = UserProfile(username, user_path)

    def login(self, username: str) -> UserProfile:
        """Sets the active user session."""
        if username not in self.users:
            user_dir = self.base_dir / username
            self.users[username] = UserProfile(username, user_dir)
            self.users[username].save()
            logger.info("New user created", username=username)
            
        self.active_user = self.users[username]
        logger.info("User logged in", username=username)
        return self.active_user

    def logout(self):
        """Clears the active session."""
        if self.active_user:
            logger.info("User logged out", username=self.active_user.username)
        self.active_user = None

    def get_current_user(self) -> Optional[UserProfile]:
        return self.active_user
