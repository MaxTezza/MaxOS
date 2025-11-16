"""System agent for health checks and service control."""
from __future__ import annotations

import subprocess
from datetime import datetime
from typing import Dict

import psutil

from max_os.agents.base import AgentRequest, AgentResponse


class SystemAgent:
    name = "system"
    description = "Inspect and remediate host services and resources"
    capabilities = ["health", "service_control", "metrics"]
    KEYWORDS = ("cpu", "memory", "service", "restart", "status", "health", "disk", "process")

    def __init__(self, config: Dict[str, object] | None = None) -> None:
        self.config = config or {}

    def can_handle(self, request: AgentRequest) -> bool:
        return request.intent.startswith("system.") or any(
            keyword in request.text.lower() for keyword in self.KEYWORDS
        )

    def handle(self, request: AgentRequest) -> AgentResponse:
        text_lower = request.text.lower()

        # Route to specific handlers
        if any(word in text_lower for word in ["health", "metrics", "stats", "status"]):
            return self._handle_health(request)
        elif any(word in text_lower for word in ["process", "processes", "ps"]):
            return self._handle_processes(request)
        elif "service" in text_lower:
            return self._handle_service(request)
        elif any(word in text_lower for word in ["disk", "storage", "space"]):
            return self._handle_disk(request)
        else:
            # Default to health check
            return self._handle_health(request)

    def _handle_health(self, request: AgentRequest) -> AgentResponse:
        """Get system health metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg()

            # Memory metrics
            mem = psutil.virtual_memory()

            # Disk metrics
            disk = psutil.disk_usage('/')

            # Uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time

            payload = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "load_average": {
                        "1min": load_avg[0],
                        "5min": load_avg[1],
                        "15min": load_avg[2],
                    },
                },
                "memory": {
                    "total_gb": round(mem.total / (1024**3), 2),
                    "available_gb": round(mem.available / (1024**3), 2),
                    "used_gb": round(mem.used / (1024**3), 2),
                    "percent": mem.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": disk.percent,
                },
                "uptime": {
                    "boot_time": boot_time.isoformat(),
                    "uptime_hours": round(uptime.total_seconds() / 3600, 2),
                },
            }

            return AgentResponse(
                agent=self.name,
                status="success",
                message="System health metrics collected successfully",
                payload=payload,
            )
        except Exception as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to collect system metrics: {str(e)}",
                payload={"error": str(e)},
            )

    def _handle_processes(self, request: AgentRequest) -> AgentResponse:
        """List running processes."""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
                try:
                    pinfo = proc.info
                    processes.append({
                        "pid": pinfo['pid'],
                        "name": pinfo['name'],
                        "user": pinfo['username'],
                        "memory_percent": round(pinfo['memory_percent'], 2),
                        "cpu_percent": round(pinfo['cpu_percent'], 2),
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Sort by memory usage and take top 20
            processes.sort(key=lambda x: x['memory_percent'], reverse=True)
            top_processes = processes[:20]

            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Found {len(processes)} processes, showing top 20 by memory",
                payload={
                    "total_count": len(processes),
                    "top_processes": top_processes,
                },
            )
        except Exception as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to list processes: {str(e)}",
                payload={"error": str(e)},
            )

    def _handle_service(self, request: AgentRequest) -> AgentResponse:
        """Check systemd service status."""
        text_lower = request.text.lower()

        # Try to extract service name from text
        # Common patterns: "check docker service", "status of nginx", etc.
        common_services = ["docker", "nginx", "apache2", "ssh", "postgresql", "mysql", "redis"]
        service_name = None

        for service in common_services:
            if service in text_lower:
                service_name = service
                break

        if not service_name:
            return AgentResponse(
                agent=self.name,
                status="error",
                message="Could not identify service name. Try specifying: docker, nginx, ssh, etc.",
                payload={"common_services": common_services},
            )

        # Check if service exists and get status
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            is_active = result.stdout.strip()

            result = subprocess.run(
                ["systemctl", "is-enabled", service_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            is_enabled = result.stdout.strip()

            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Service {service_name} status retrieved",
                payload={
                    "service": service_name,
                    "active": is_active,
                    "enabled": is_enabled,
                },
            )
        except subprocess.TimeoutExpired:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Timeout checking service {service_name}",
                payload={"service": service_name},
            )
        except Exception as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to check service {service_name}: {str(e)}",
                payload={"error": str(e), "service": service_name},
            )

    def _handle_disk(self, request: AgentRequest) -> AgentResponse:
        """Get disk usage for all partitions."""
        try:
            partitions = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partitions.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "percent": usage.percent,
                    })
                except PermissionError:
                    # Skip partitions we can't access
                    pass

            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Retrieved disk usage for {len(partitions)} partition(s)",
                payload={
                    "count": len(partitions),
                    "partitions": partitions,
                },
            )
        except Exception as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to get disk usage: {str(e)}",
                payload={"error": str(e)},
            )
