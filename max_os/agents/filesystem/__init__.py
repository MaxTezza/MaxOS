"""Filesystem agent stub: responsible for file CRUD, search, organization."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

from max_os.agents.base import AgentRequest, AgentResponse


class FileSystemAgent:
    name = "filesystem"
    description = "Manage files, directories, backups, and package installs"
    capabilities = ["search", "organize", "archive", "package_install"]
    KEYWORDS: Iterable[str] = (
        "file",
        "folder",
        "directory",
        "archive",
        "backup",
        "move",
        "copy",
        "install",
    )

    def __init__(self, config: Dict[str, object] | None = None) -> None:
        self.config = config or {}
        whitelist = self.config.get("root_whitelist", ["/home"])
        self.allowed_roots = [Path(path).resolve() for path in whitelist]

    def can_handle(self, request: AgentRequest) -> bool:
        return request.intent.startswith("file.") or any(
            keyword in request.text.lower() for keyword in self.KEYWORDS
        )

    def handle(self, request: AgentRequest) -> AgentResponse:
        summary = {
            "dry_run": True,
            "allowed_roots": [str(p) for p in self.allowed_roots],
            "next_steps": [
                "Translate natural request into concrete filesystem plan",
                "Validate plan against PolicyKit + whitelist",
                "Show diff/preview to user before execution",
            ],
        }
        return AgentResponse(
            agent=self.name,
            status="planned",
            message="Filesystem agent prepared an execution plan (dry-run only).",
            payload=summary,
        )
