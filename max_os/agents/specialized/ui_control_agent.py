"""
MaxOS UI Control Agent.
Enables automation of non-AI applications using xdotool.
"""

import asyncio
import subprocess
from typing import Dict, Any, Optional

import structlog
from max_os.agents.base import AgentRequest, AgentResponse, BaseAgent

logger = structlog.get_logger("max_os.agents.ui_control")

class UIControlAgent(BaseAgent):
    name = "ui_control"
    description = "Drives third-party applications using keyboard and mouse automation"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.config = config or {}
        self._check_xdotool()

    def _check_xdotool(self):
        try:
            subprocess.run(["xdotool", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.xdotool_available = True
        except FileNotFoundError:
            logger.warning("xdotool not found. UI Control will be disabled.")
            self.xdotool_available = False

    def can_handle(self, request: AgentRequest) -> bool:
        keywords = ["click", "type", "minimize", "maximize", "close window", "press keys", "scroll"]
        return any(k in request.text.lower() for k in keywords) or request.intent == "system.ui_control"

    async def handle(self, request: AgentRequest) -> AgentResponse:
        if not self.xdotool_available:
            return AgentResponse(
                agent=self.name,
                status="error",
                message="UI Control is unavailable because xdotool is not installed on this system.",
                payload={}
            )

        text_lower = request.text.lower()
        
        # Simple heuristic-based mapping for commands
        # A more advanced version would use Gemini to generate the xdotool script
        try:
            if "minimize" in text_lower:
                subprocess.run(["xdotool", "getactivewindow", "windowminimize"])
                return AgentResponse(agent=self.name, status="success", message="Minimized active window.")
            
            elif "close" in text_lower and "window" in text_lower:
                subprocess.run(["xdotool", "getactivewindow", "windowkill"])
                return AgentResponse(agent=self.name, status="success", message="Closed active window.")

            elif "type" in text_lower:
                # Extract text between quotes if possible
                import re
                match = re.search(r'["\'](.*?)["\']', request.text)
                if match:
                    content = match.group(1)
                    subprocess.run(["xdotool", "type", content])
                    return AgentResponse(agent=self.name, status="success", message=f"Typed: {content}")
            
            # Placeholder for complex coordinated clicks (requires Vision coordinates)
            return AgentResponse(
                agent=self.name,
                status="success",
                message="I understand the command, but I'm still learning the visual coordinates for complex clicks. I can currently minimize/close windows and type text.",
                payload={}
            )

        except Exception as e:
            logger.error("UI Control error", error=str(e))
            return AgentResponse(agent=self.name, status="error", message=f"Failed to control UI: {str(e)}")
