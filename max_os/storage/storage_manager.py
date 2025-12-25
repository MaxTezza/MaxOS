"""Unified storage manager - Redis (hot) + SQLite (local) + Firestore (cloud)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

try:
    import redis
except ImportError:  # pragma: no cover - redis optional
    redis = None

from max_os.storage.firestore_client import FirestoreClient


class StorageManager:
    """Unified storage manager - Redis (hot) + SQLite (local) + Firestore (cloud)."""

    def __init__(
        self,
        redis_url: str,
        sqlite_path: str,
        firestore_project: str,
        offline_mode: bool = False,
    ):
        """Initialize storage manager with three-tier storage.

        Args:
            redis_url: Redis connection URL
            sqlite_path: Path to SQLite database file
            firestore_project: Google Cloud project ID for Firestore
            offline_mode: If True, disable Firestore cloud sync

        Raises:
            ImportError: If redis is not installed
        """
        if redis is None:
            raise ImportError("redis is required. Install with: pip install redis")

        self.redis = redis.from_url(redis_url, decode_responses=True)
        sqlite_path_expanded = Path(sqlite_path).expanduser()
        sqlite_path_expanded.parent.mkdir(parents=True, exist_ok=True)
        self.sqlite = sqlite3.connect(str(sqlite_path_expanded))
        self.firestore = None if offline_mode else FirestoreClient(firestore_project)
        self.offline_mode = offline_mode

        self._init_sqlite()

    def _init_sqlite(self):
        """Initialize SQLite schema."""
        cursor = self.sqlite.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                voice_input TEXT,
                gemini_response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                synced_to_firestore BOOLEAN DEFAULT 0
            )
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_timestamp 
            ON conversations(user_id, timestamp)
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        self.sqlite.commit()

    async def store_conversation(
        self,
        user_id: str,
        voice_input: str,
        vision_context: dict | None = None,
        gemini_response: str | None = None,
        audio_data: bytes | None = None,
        image_data: bytes | None = None,
    ):
        """Store conversation in all layers.

        Args:
            user_id: User identifier
            voice_input: Voice transcription text
            vision_context: Optional vision analysis results
            gemini_response: Optional Gemini response text
            audio_data: Optional audio bytes to upload
            image_data: Optional image bytes to upload
        """
        # 1. Hot cache (Redis) - for current session
        self.redis.setex(
            f"session:{user_id}:last_command",
            3600,  # 1 hour TTL
            voice_input,
        )

        # 2. Local persistent (SQLite) - for audit/offline
        cursor = self.sqlite.cursor()
        cursor.execute(
            """
            INSERT INTO conversations 
            (user_id, voice_input, gemini_response, timestamp)
            VALUES (?, ?, ?, datetime('now'))
        """,
            (user_id, voice_input, gemini_response),
        )
        self.sqlite.commit()

        # 3. Cloud persistent (Firestore) - for sync/multimodal
        if not self.offline_mode and self.firestore:
            audio_url = None
            image_url = None

            if audio_data:
                audio_url = await self.firestore.upload_audio(
                    f"conversations/{user_id}/{datetime.now().timestamp()}.wav",
                    audio_data,
                )

            if image_data:
                image_url = await self.firestore.upload_image(
                    f"conversations/{user_id}/{datetime.now().timestamp()}.jpg",
                    image_data,
                )

            await self.firestore.add_conversation(
                user_id,
                voice_input,
                vision_context,
                gemini_response,
                audio_url,
                image_url,
            )

    async def get_conversation_history(self, user_id: str, limit: int = 50) -> list[dict]:
        """Get conversation history (Firestore first, SQLite fallback).

        Args:
            user_id: User identifier
            limit: Maximum number of conversations to retrieve

        Returns:
            List of conversation dictionaries
        """
        if not self.offline_mode and self.firestore:
            return await self.firestore.get_conversation_history(user_id, limit)

        # Fallback to SQLite
        cursor = self.sqlite.cursor()
        cursor.execute(
            """
            SELECT voice_input, gemini_response, timestamp
            FROM conversations
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (user_id, limit),
        )

        return [
            {
                "voice_input": row[0],
                "gemini_response": row[1],
                "timestamp": row[2],
            }
            for row in cursor.fetchall()
        ]

    async def sync_pantry(self, user_id: str, items: list[dict]):
        """Sync pantry to Firestore.

        Args:
            user_id: User identifier
            items: List of pantry item dictionaries
        """
        if not self.offline_mode and self.firestore:
            await self.firestore.update_pantry(user_id, items)

    async def get_pantry(self, user_id: str) -> list[dict]:
        """Get pantry from Firestore (with local cache).

        Args:
            user_id: User identifier

        Returns:
            List of pantry item dictionaries
        """
        # Check Redis cache first
        cached = self.redis.get(f"pantry:{user_id}")
        if cached:
            return json.loads(cached)

        # Fetch from Firestore
        if not self.offline_mode and self.firestore:
            pantry = await self.firestore.get_pantry(user_id)

            # Cache in Redis
            self.redis.setex(f"pantry:{user_id}", 3600, json.dumps(pantry))

            return pantry

        return []
