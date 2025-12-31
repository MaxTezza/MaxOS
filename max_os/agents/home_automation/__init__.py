"""
Home Automation Agent: Controls smart home devices (Lights, Thermostat, etc.).
Currently designed to interface with Google Home Graph API or Home Assistant.
"""

from typing import Any, Dict, Optional

import structlog

from max_os.agents.base import AgentRequest, AgentResponse, BaseAgent

logger = structlog.get_logger("max_os.agents.home_automation")

class HomeAutomationAgent:
    name = "home_automation"
    description = "Controls smart home devices (Lights, Thermostat, Doorbell)"
    capabilities = ["light_control", "thermostat_control", "security_control"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        # Placeholder state for "mock" automation
        self.devices = {
            "living room lights": "off",
            "kitchen lights": "off",
            "thermostat": 72,
            "front door": "locked"
        }

    def can_handle(self, request: AgentRequest) -> bool:
        if request.intent.startswith("home."):
            return True
            
        keywords = [
            "lights", "turn on", "turn off", "dim", "thermostat", "temperature", 
            "door", "lock", "unlock", "set temp"
        ]
        # Only handle if one of the specific device words is also present
        device_words = ["light", "thermostat", "door", "heat", "cool"]
        
        has_keyword = any(kw in request.text.lower() for kw in keywords)
        has_device = any(dw in request.text.lower() for dw in device_words)
        
        return has_keyword and has_device

    async def handle(self, request: AgentRequest) -> AgentResponse:
        text = request.text.lower()
        
        if "light" in text:
            return await self._handle_lights(text)
        elif "thermostat" in text or "temp" in text:
            return await self._handle_thermostat(text)
        elif "door" in text:
            return await self._handle_lock(text)
            
        return AgentResponse(
             agent=self.name,
             status="unhandled",
             message="I'm not sure which device you want to control.",
             payload={}
        )

    async def _handle_lights(self, text: str) -> AgentResponse:
        state = "on" if "on" in text else "off"
        # Determine room (simple heuristic)
        room = "living room" if "living" in text else ("kitchen" if "kitchen" in text else "all")
        
        msg = f"Turning {state} {room} lights."
        
        # In a real implementation, this would call Google Home Graph API
        # or Home Assistant API
        if room == "all":
            self.devices["living room lights"] = state
            self.devices["kitchen lights"] = state
        else:
            key = f"{room} lights"
            if key in self.devices:
                self.devices[key] = state
            else:
                msg = f"I couldn't find lights in the {room}."
                return AgentResponse(agent=self.name, status="error", message=msg)

        return AgentResponse(
            agent=self.name,
            status="success",
            message=msg,
            payload={"action": "lights", "state": state, "room": room}
        )

    async def _handle_thermostat(self, text: str) -> AgentResponse:
        # "Set thermostat to 75"
        import re
        match = re.search(r'\b(\d{2})\b', text)
        if match:
            temp = int(match.group(1))
            self.devices["thermostat"] = temp
            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Thermostat set to {temp}°F.",
                payload={"action": "thermostat", "temp": temp}
            )
            
        return AgentResponse(agent=self.name, status="info", message=f"Current temperature is {self.devices['thermostat']}°F.")

    async def _handle_lock(self, text: str) -> AgentResponse:
        # "Unlock front door"
        if "unlock" in text:
            state = "unlocked"
        elif "lock" in text:
            state = "locked"
        else:
            return AgentResponse(agent=self.name, status="info", message=f"Front door is {self.devices['front door']}.")

        self.devices["front door"] = state
        return AgentResponse(
            agent=self.name,
            status="success",
            message=f"Front door {state}.",
            payload={"action": "lock", "state": state}
        )
