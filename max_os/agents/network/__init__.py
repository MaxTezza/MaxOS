"""Network agent for Wi-Fi, VPN, and firewall automation."""

from __future__ import annotations

import socket
import subprocess

import psutil

from max_os.agents.base import AgentRequest, AgentResponse


class NetworkAgent:
    name = "network"
    description = "Configure interfaces, VPNs, and firewalls"
    capabilities = ["wifi", "vpn", "firewall", "diagnostics"]
    KEYWORDS = ("wifi", "network", "vpn", "firewall", "connect", "ip", "interface", "ping")

    def __init__(self, config: dict[str, object] | None = None) -> None:
        self.config = config or {}
        self.allowed_interfaces = self.config.get("allowed_interfaces", [])

    def can_handle(self, request: AgentRequest) -> bool:
        return request.intent.startswith("network.") or any(
            keyword in request.text.lower() for keyword in self.KEYWORDS
        )

    async def handle(self, request: AgentRequest) -> AgentResponse:
        text_lower = request.text.lower()

        # Route to specific handlers
        if any(word in text_lower for word in ["interface", "interfaces", "ip", "address"]):
            return self._handle_interfaces(request)
        elif any(word in text_lower for word in ["ping", "connectivity", "reachable"]):
            return self._handle_ping(request)
        elif any(word in text_lower for word in ["dns", "lookup", "resolve"]):
            return self._handle_dns(request)
        elif any(word in text_lower for word in ["connection", "connections", "network stats"]):
            return self._handle_connections(request)
        else:
            # Default to showing interfaces
            return self._handle_interfaces(request)

    def _handle_interfaces(self, request: AgentRequest) -> AgentResponse:
        """List network interfaces and their addresses."""
        try:
            interfaces = []
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()

            for iface_name, addr_list in addrs.items():
                iface_info = {
                    "name": iface_name,
                    "addresses": [],
                    "is_up": stats[iface_name].isup if iface_name in stats else False,
                }

                for addr in addr_list:
                    if addr.family == socket.AF_INET:
                        iface_info["addresses"].append(
                            {
                                "type": "IPv4",
                                "address": addr.address,
                                "netmask": addr.netmask,
                            }
                        )
                    elif addr.family == socket.AF_INET6:
                        iface_info["addresses"].append(
                            {
                                "type": "IPv6",
                                "address": addr.address,
                            }
                        )

                interfaces.append(iface_info)

            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Retrieved {len(interfaces)} network interface(s)",
                payload={
                    "count": len(interfaces),
                    "interfaces": interfaces,
                },
            )
        except Exception as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to get network interfaces: {str(e)}",
                payload={"error": str(e)},
            )

    def _handle_ping(self, request: AgentRequest) -> AgentResponse:
        """Ping a host to check connectivity."""
        # Extract hostname/IP from text
        target = None

        # Common patterns: "ping google.com", "check if 8.8.8.8 is reachable"
        words = request.text.split()
        for i, word in enumerate(words):
            if word.lower() in ["ping", "check", "test"]:
                if i + 1 < len(words):
                    potential_target = words[i + 1]
                    # Basic validation
                    if "." in potential_target or ":" in potential_target:
                        target = potential_target.strip(",.?!")
                        break

        if not target:
            # Default to a common host
            target = "8.8.8.8"

        try:
            result = subprocess.run(
                ["ping", "-c", "4", "-W", "2", target],
                capture_output=True,
                text=True,
                timeout=10,
            )

            success = result.returncode == 0
            lines = result.stdout.strip().split("\n")

            # Parse statistics
            stats_line = [line for line in lines if "packets transmitted" in line]
            rtt_line = [line for line in lines if "rtt min/avg/max" in line or "round-trip" in line]

            stats = {}
            if stats_line:
                # Example: "4 packets transmitted, 4 received, 0% packet loss, time 3004ms"
                parts = stats_line[0].split(",")
                for part in parts:
                    if "transmitted" in part:
                        stats["transmitted"] = int(part.split()[0])
                    elif "received" in part:
                        stats["received"] = int(part.split()[0])
                    elif "packet loss" in part:
                        stats["packet_loss"] = part.split()[0].strip()

            if rtt_line:
                # Example: "rtt min/avg/max/mdev = 10.123/15.456/20.789/3.456 ms"
                rtt_part = rtt_line[0].split("=")[1].strip() if "=" in rtt_line[0] else ""
                if rtt_part:
                    stats["rtt"] = rtt_part

            return AgentResponse(
                agent=self.name,
                status="success" if success else "error",
                message=f"Ping to {target} {'succeeded' if success else 'failed'}",
                payload={
                    "target": target,
                    "reachable": success,
                    "statistics": stats,
                },
            )
        except subprocess.TimeoutExpired:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Ping to {target} timed out",
                payload={"target": target},
            )
        except Exception as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to ping {target}: {str(e)}",
                payload={"error": str(e), "target": target},
            )

    def _handle_dns(self, request: AgentRequest) -> AgentResponse:
        """Perform DNS lookup."""
        # Extract hostname from text
        words = request.text.split()
        hostname = None

        for i, word in enumerate(words):
            if word.lower() in ["lookup", "resolve", "dns"]:
                if i + 1 < len(words):
                    hostname = words[i + 1].strip(",.?!")
                    break

        if not hostname:
            return AgentResponse(
                agent=self.name,
                status="error",
                message="Could not identify hostname to lookup",
                payload={"text": request.text},
            )

        try:
            # Get IP addresses
            ip_addresses = socket.getaddrinfo(hostname, None)
            unique_ips = list(set([addr[4][0] for addr in ip_addresses]))

            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"DNS lookup for {hostname} found {len(unique_ips)} address(es)",
                payload={
                    "hostname": hostname,
                    "addresses": unique_ips,
                },
            )
        except socket.gaierror as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to resolve {hostname}",
                payload={"hostname": hostname, "error": str(e)},
            )
        except Exception as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"DNS lookup failed: {str(e)}",
                payload={"hostname": hostname, "error": str(e)},
            )

    def _handle_connections(self, request: AgentRequest) -> AgentResponse:
        """Show active network connections."""
        try:
            connections = []
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "ESTABLISHED":
                    connections.append(
                        {
                            "local_address": (
                                f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None
                            ),
                            "remote_address": (
                                f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None
                            ),
                            "status": conn.status,
                            "pid": conn.pid,
                        }
                    )

            # Get network IO stats
            io_stats = psutil.net_io_counters()

            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Found {len(connections)} established connection(s)",
                payload={
                    "connections": connections[:50],  # Limit to 50
                    "total_connections": len(connections),
                    "io_statistics": {
                        "bytes_sent": io_stats.bytes_sent,
                        "bytes_recv": io_stats.bytes_recv,
                        "packets_sent": io_stats.packets_sent,
                        "packets_recv": io_stats.packets_recv,
                    },
                },
            )
        except Exception as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to get network connections: {str(e)}",
                payload={"error": str(e)},
            )
