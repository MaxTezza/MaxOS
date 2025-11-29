"""Simple in-memory transcript store with disk persistence hook."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

try:
    import redis
except ImportError:  # pragma: no cover - redis optional for local runs
    redis = None

from max_os.agents.base import AgentResponse
from max_os.utils.config import Settings


@dataclass
class MemoryItem:
    role: str
    content: str


@dataclass
class ConversationMemory:
    limit: int = 20
    history: list[MemoryItem] = field(default_factory=list)
    settings: Settings | None = None
    redis_client: redis.Redis | None = None

    def __post_init__(self):
        if (
            redis
            and self.settings
            and self.settings.orchestrator.get("memory_backend", "").startswith("redis://")
        ):
            self.redis_client = redis.from_url(self.settings.orchestrator["memory_backend"])

    def add_user(self, text: str) -> None:
        self._append(MemoryItem(role="user", content=text))

    def add_agent(self, response: AgentResponse) -> None:
        message = f"{response.agent}: {response.message}"
        self._append(MemoryItem(role="assistant", content=message))

    def serialize(self) -> list[dict]:
        return [item.__dict__ for item in self.get_history()]

    def dump(self, path: Path) -> None:
        data = "\n".join(f"[{item.role}] {item.content}" for item in self.get_history())
        path.write_text(data, encoding="utf-8")

    def _append(self, item: MemoryItem) -> None:
        if self.redis_client:
            self.redis_client.lpush("conversation_history", json.dumps(item.__dict__))
            self.redis_client.ltrim("conversation_history", 0, self.limit - 1)
        else:
            self.history.append(item)
            if len(self.history) > self.limit:
                self.history = self.history[-self.limit :]

    def get_history(self) -> list[MemoryItem]:
        if self.redis_client:
            history = []
            for item in self.redis_client.lrange("conversation_history", 0, -1):
                data = json.loads(item)
                history.append(MemoryItem(role=data["role"], content=data["content"]))
            return history
        else:
            return self.history
