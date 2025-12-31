"""
App Launcher Agent: Opens, closes, and manages applications.
Uses standard Linux commands (gtk-launch, wmctrl, pkill) to control apps.
"""

import subprocess
from typing import Any, Dict, Optional

import structlog

from max_os.agents.base import AgentRequest, AgentResponse, BaseAgent

logger = structlog.get_logger("max_os.agents.app_launcher")

class AppLauncherAgent(BaseAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.name = "app_launcher"
        self.description = "Launches, closes, and manages system applications"
        # Common apps mapping for easier voice matching
        self.app_aliases = {
            "browser": "firefox",
            "chrome": "google-chrome",
            "terminal": "gnome-terminal",
            "editor": "code",
            "spotify": "spotify",
            "file manager": "nautilus",
            "calculator": "gnome-calculator",
        }

    def can_handle(self, request: AgentRequest) -> bool:
        # Check intent or keywords
        if request.intent.startswith("app."):
            return True
        
        keywords = ["open", "launch", "start", "close", "quit", "kill", "switch to", "type", "press", "click", "hit"]
        return any(kw in request.text.lower() for kw in keywords)

    async def handle(self, request: AgentRequest) -> AgentResponse:
        intent = request.intent
        text = request.text.lower()
        
        if "close" in text or "quit" in text or "kill" in text:
            return await self._close_app(text)
        elif "open" in text or "launch" in text or "start" in text:
            return await self._launch_app(text)
        elif "switch" in text:
            return await self._switch_window(text)
        elif "type" in text:
            return await self._type_text(request.text) # Use original case for typing
        elif "press" in text or "hit" in text:
            return await self._press_key(text)
            
        return AgentResponse(
             agent=self.name,
             status="error",
             message="I didn't understand what you want to do with the app.",
             payload={}
        )

    async def _type_text(self, text: str) -> AgentResponse:
        # "type hello world" -> types "hello world"
        content = text
        if "type " in text.lower():
            # simple extraction: everything after "type "
            idx = text.lower().find("type ") + 5
            content = text[idx:]
            
        try:
            # Requires xdotool
            subprocess.run(["xdotool", "type", "--delay", "50", content], check=True)
            return AgentResponse(
                agent=self.name, 
                status="success", 
                message=f"Typed: {content}",
                payload={"action": "type", "content": content}
            )
        except Exception as e:
            return AgentResponse(agent=self.name, status="error", message="Failed to type text. Is xdotool installed?", payload={"error": str(e)})

    async def _press_key(self, text: str) -> AgentResponse:
        # "press enter", "hit ctrl+c"
        key = ""
        if "press " in text:
            key = text.split("press ")[1].split()[0]
        elif "hit " in text:
            key = text.split("hit ")[1].split()[0]
            
        if not key:
            return AgentResponse(agent=self.name, status="error", message="Which key should I press?")
            
        try:
            subprocess.run(["xdotool", "key", key], check=True)
            return AgentResponse(
                 agent=self.name,
                 status="success",
                 message=f"Pressed {key}",
                 payload={"action": "press_key", "key": key}
            )
        except Exception as e:
            return AgentResponse(agent=self.name, status="error", message=f"Failed to press {key}.", payload={"error": str(e)})


    async def _launch_app(self, text: str) -> AgentResponse:
        app_name = self._extract_app_name(text)
        if not app_name:
             return AgentResponse(
                 agent=self.name,
                 status="error",
                 message="I couldn't identify the application name.",
                 payload={}
             )

        try:
            # Use gtk-launch or directly run
            # Note: subprocess.Popen is non-blocking
            subprocess.Popen([app_name], start_new_session=True)
            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Launching {app_name}...",
                payload={"action": "launch", "app": app_name}
            )
        except FileNotFoundError:
             return AgentResponse(
                 agent=self.name,
                 status="error",
                 message=f"I couldn't find an application named '{app_name}'.",
                 payload={"error": "not_found", "app": app_name}
             )
        except Exception as e:
            logger.error("Launch failed", error=str(e))
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to launch {app_name}.",
                payload={"error": str(e)}
            )

    async def _close_app(self, text: str) -> AgentResponse:
        app_name = self._extract_app_name(text)
        if not app_name:
             return AgentResponse(agent=self.name, status="error", message="Which app should I close?")

        try:
            # aggressive kill for now, maybe use wmctrl -c later for grace
            subprocess.run(["pkill", "-f", app_name], check=True)
            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Closed {app_name}.",
                payload={"action": "close", "app": app_name}
            )
        except subprocess.CalledProcessError:
             return AgentResponse(
                 agent=self.name,
                 status="error",
                 message=f"{app_name} doesn't seem to be running.",
                 payload={"error": "not_running"}
             )

    async def _switch_window(self, text: str) -> AgentResponse:
        # Placeholder for wmctrl usage
        return AgentResponse(agent=self.name, status="info", message="Window switching not yet implemented.")

    def _extract_app_name(self, text: str) -> str:
        # Simple heuristic extraction
        # "open firefox" -> "firefox"
        # "launch google chrome" -> "google-chrome"
        
        words = text.split()
        triggers = ["open", "launch", "start", "close", "quit", "kill"]
        
        found_trigger = False
        potential_name = []
        
        for word in words:
            if word in triggers:
                found_trigger = True
                continue
            if found_trigger:
                potential_name.append(word)
        
        raw_name = " ".join(potential_name).strip()
        
        # Check aliases
        return self.app_aliases.get(raw_name, raw_name)
