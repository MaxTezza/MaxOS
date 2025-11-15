"""Simple in-memory transcript store with disk persistence hook."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from max_os.agents.base import AgentResponse


@dataclass
class MemoryItem:
    role: str
    content: str


@dataclass
class ConversationMemory:
    limit: int = 20
    history: List[MemoryItem] = field(default_factory=list)

    def add_user(self, text: str) -> None:
        self._append(MemoryItem(role="user", content=text))

    def add_agent(self, response: AgentResponse) -> None:
        message = f"{response.agent}: {response.message}"
        self._append(MemoryItem(role="assistant", content=message))

    def serialize(self) -> List[dict]:
        return [item.__dict__ for item in self.history]

    def dump(self, path: Path) -> None:
        data = "\n".join(f"[{item.role}] {item.content}" for item in self.history)
        path.write_text(data, encoding="utf-8")

    def _append(self, item: MemoryItem) -> None:
        self.history.append(item)
        if len(self.history) > self.limit:
            self.history = self.history[-self.limit :]
