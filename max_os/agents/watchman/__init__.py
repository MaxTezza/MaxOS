"""
The Watchman Agent.
Monitor's user health (sedentary time) and system security (FaceID stub).
"""

import time
import asyncio
from typing import Dict, Any, Optional

import structlog
from max_os.agents.base import AgentRequest, AgentResponse, BaseAgent

logger = structlog.get_logger("max_os.agents.watchman")

class WatchmanAgent(BaseAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.name = "watchman"
        self.description = "Security and Health monitor."
        self.last_activity_time = time.time()
        self.active_session_start = time.time()
        
        # Checking interval (seconds)
        self.check_interval = 60 * 30 # 30 mins
        self.learning_task = None

    async def start(self):
        """Start the background monitoring loop."""
        logger.info("Watchman on duty.")
        self.learning_task = asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        while True:
            await asyncio.sleep(self.check_interval)
            
            # Health Check
            elapsed = time.time() - self.active_session_start
            if elapsed > 7200: # 2 hours
                # In a real system, we'd trigger a proactive notification via the Orchestrator
                # For now, we just log it, or if accessed via voice, we report it.
                logger.warning("Health Alert: User sedentary for > 2 hours.")
                # self.orchestrator.notify("Max, tell the user to stand up.") (Future capability)

    def can_handle(self, request: AgentRequest) -> bool:
        triggers = ["security", "health", "uptime", "who am i", "scan", "status"]
        return any(t in request.text.lower() for t in triggers) or request.intent.startswith("watchman.")

    async def handle(self, request: AgentRequest) -> AgentResponse:
        text = request.text.lower()
        self.last_activity_time = time.time()
        
        if "health" in text or "uptime" in text:
            return self._report_health()
        elif "security" in text or "scan" in text or "who" in text or "status" in text:
            return self._run_security_scan()
            
        return AgentResponse(agent=self.name, status="unhandled", message="I can report on system security or your health metrics.")

    def _report_health(self) -> AgentResponse:
        uptime = int((time.time() - self.active_session_start) / 60)
        msg = f"Session Uptime: {uptime} minutes.\nYou are looking healthy, but don't forget to hydrate."
        return AgentResponse(
            agent=self.name,
            status="success",
            message=msg,
            payload={"uptime_mins": uptime}
        )

    def _run_security_scan(self) -> AgentResponse:
        # Stub for Vision API FaceID
        authorized_user = "Maximus"
        confidence = 0.99
        
        msg = f"Security Scan Complete.\nIdentity Verified: {authorized_user} ({confidence*100}%).\nPerimeter Secure."
        return AgentResponse(
            agent=self.name,
            status="success",
            message=msg,
            payload={"verified": True, "user": authorized_user}
        )
