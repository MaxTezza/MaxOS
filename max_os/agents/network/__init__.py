"""Network agent stub for Wi-Fi, VPN, and firewall automation."""
from __future__ import annotations

from typing import Dict

from max_os.agents.base import AgentRequest, AgentResponse


class NetworkAgent:
    name = "network"
    description = "Configure interfaces, VPNs, and firewalls"
    capabilities = ["wifi", "vpn", "firewall", "diagnostics"]
    KEYWORDS = ("wifi", "network", "vpn", "firewall", "connect", "ip")

    def __init__(self, config: Dict[str, object] | None = None) -> None:
        self.config = config or {}
        self.allowed_interfaces = self.config.get("allowed_interfaces", [])

    def can_handle(self, request: AgentRequest) -> bool:
        return request.intent.startswith("network.") or any(
            keyword in request.text.lower() for keyword in self.KEYWORDS
        )

    def handle(self, request: AgentRequest) -> AgentResponse:
        payload = {
            "interfaces": self.allowed_interfaces,
            "next_steps": [
                "Map natural language to NetworkManager D-Bus calls",
                "Request PolicyKit auth for privileged actions",
                "Return connection profile and status",
            ],
        }
        return AgentResponse(
            agent=self.name,
            status="planned",
            message="Network workflow drafted (no live D-Bus calls yet).",
            payload=payload,
        )
