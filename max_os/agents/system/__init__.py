"""System agent stub for health checks and service control."""
from __future__ import annotations

from datetime import datetime
from typing import Dict

from max_os.agents.base import AgentRequest, AgentResponse


class SystemAgent:
    name = "system"
    description = "Inspect and remediate host services and resources"
    capabilities = ["health", "service_control", "metrics"]
    KEYWORDS = ("cpu", "memory", "service", "restart", "status", "health")

    def __init__(self, config: Dict[str, object] | None = None) -> None:
        self.config = config or {}

    def can_handle(self, request: AgentRequest) -> bool:
        return request.intent.startswith("system.") or any(
            keyword in request.text.lower() for keyword in self.KEYWORDS
        )

    def handle(self, request: AgentRequest) -> AgentResponse:
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": {
                "cpu_load": "TODO",
                "memory_used": "TODO",
            },
            "allowed_units": self.config.get("allowed_units", []),
        }
        return AgentResponse(
            agent=self.name,
            status="pending_confirmation",
            message="System diagnostics collected (placeholder metrics).",
            payload=payload,
        )
