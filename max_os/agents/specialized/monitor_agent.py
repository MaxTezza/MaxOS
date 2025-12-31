"""
MaxOS Monitor Agent.
Proactively monitors system health and provides alerts.
"""

from max_os.agents.base import AgentRequest, AgentResponse, BaseAgent
import structlog

logger = structlog.get_logger("max_os.agents.monitor")

class MonitorAgent(BaseAgent):
    name = "monitor"
    description = "Proactively monitors system health and resource usage"
    
    def __init__(self, system_manager=None):
        super().__init__()
        self.system = system_manager
        
    def can_handle(self, request: AgentRequest) -> bool:
        keywords = ["how is the computer", "system health", "is everything okay", "usage", "cpu", "ram"]
        return any(k in request.text.lower() for k in keywords) or request.intent == "system.monitor"

    async def handle(self, request: AgentRequest) -> AgentResponse:
        if not self.system:
            return AgentResponse(
                agent=self.name,
                status="error",
                message="System manager not linked to Monitor Agent.",
                payload={}
            )
            
        health = self.system.get_system_health()
        
        # Determine a human-friendly assessment
        cpu = health["cpu_usage"]
        mem_pct = health["memory"]["percent"]
        disk_pct = health["disk"]["percent"]
        
        assessment = "Everything looks normal."
        if cpu > 80:
            assessment = "The CPU is working quite hard right now."
        elif mem_pct > 90:
            assessment = "Memory is critically low."
        elif disk_pct > 95:
            assessment = "You are almost out of disk space."
            
        message = f"System Health: {assessment} CPU: {cpu}%, Memory: {mem_pct}%, Disk: {disk_pct}%."
        
        return AgentResponse(
            agent=self.name,
            status="success",
            message=message,
            payload=health
        )
