"""
MaxOS System Manager.
Handles process lifecycle (launch, track, kill) and hardware status.
"""

import os
import signal
import subprocess
import psutil
import structlog
from typing import Dict, Any, Optional

logger = structlog.get_logger("max_os.system")

class ProcessManager:
    """Manages external processes launched by MaxOS."""
    
    def __init__(self):
        self.active_processes: Dict[str, int] = {} # Name -> PID
        
    def track_process(self, name: str, pid: int):
        """Adds a process to the tracking list."""
        self.active_processes[name] = pid
        logger.info("Process tracked", name=name, pid=pid)
        
    def kill_process(self, name: str) -> bool:
        """Terminates a process by name."""
        if name in self.active_processes:
            pid = self.active_processes[name]
            try:
                os.kill(pid, signal.SIGTERM)
                del self.active_processes[name]
                logger.info("Process terminated", name=name, pid=pid)
                return True
            except ProcessLookupError:
                logger.warning("Process not found", name=name, pid=pid)
                del self.active_processes[name]
                return False
            except Exception as e:
                logger.error("Failed to kill process", name=name, error=str(e))
                return False
        return False

    def get_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Gets resource usage for a tracked process."""
        if name in self.active_processes:
            pid = self.active_processes[name]
            try:
                proc = psutil.Process(pid)
                return {
                    "name": name,
                    "pid": pid,
                    "status": proc.status(),
                    "cpu_percent": proc.cpu_percent(),
                    "memory_mb": proc.memory_info().rss / (1024 * 1024)
                }
            except Exception:
                return None
        return None

class SystemManager:
    """High-level system controller."""
    
    def __init__(self):
        self.processes = ProcessManager()
        
    def get_system_health(self) -> Dict[str, Any]:
        """Returns global system resource usage."""
        return {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage('/')._asdict(),
            "temp": self._get_temperature()
        }
        
    def _get_temperature(self) -> Optional[float]:
        """Placeholder for thermal monitoring."""
        try:
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps:
                return temps['coretemp'][0].current
        except Exception:
            pass
        return None
