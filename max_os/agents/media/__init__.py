"""
Media Agent: Controls system volume and media playback.
Supports:
- System Volume (pactl/amixer)
- Media Player Controls (mpris via playerctl) - standard on Linux for Spotify, VLC, etc.
"""

import shutil
import subprocess
from typing import Any, Dict, Optional

import structlog

from max_os.agents.base import AgentRequest, AgentResponse, BaseAgent

logger = structlog.get_logger("max_os.agents.media")

class MediaAgent:
    name = "media"
    description = "Controls media playback (volume, play/pause, next) and music"
    capabilities = ["volume_control", "playback_control"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Check for playerctl
        self.has_playerctl = shutil.which("playerctl") is not None

    def can_handle(self, request: AgentRequest) -> bool:
        if request.intent.startswith("media."):
            return True
            
        keywords = [
            "play", "pause", "stop music", "next song", "previous song", 
            "skip track", "volume", "turn up", "turn down", "mute", "unmute"
        ]
        return any(kw in request.text.lower() for kw in keywords)

    async def handle(self, request: AgentRequest) -> AgentResponse:
        text = request.text.lower()
        
        # Volume Controls
        if "volume" in text or "turn up" in text or "turn down" in text or "mute" in text:
            return await self._handle_volume(text)
            
        # Playback Controls
        if self.has_playerctl:
             return await self._handle_playback(text)
        else:
             return AgentResponse(
                 agent=self.name,
                 status="error",
                 message="I need 'playerctl' installed to control music. (sudo apt install playerctl)",
                 payload={"error": "missing_dependency"}
             )

    async def _handle_volume(self, text: str) -> AgentResponse:
        try:
            cmd = []
            msg = ""
            
            if "mute" in text and "unmute" not in text:
                cmd = ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"]
                msg = "Muted system volume."
            elif "unmute" in text:
                cmd = ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"]
                msg = "Unmuted system volume."
            elif "up" in text or "louder" in text or "increase" in text:
                cmd = ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"]
                msg = "Increased volume."
            elif "down" in text or "quieter" in text or "decrease" in text:
                cmd = ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"]
                msg = "Decreased volume."
            elif "set" in text and "%" in text:
                # Extract percentage (heuristic)
                for word in text.split():
                    if word.endswith("%"):
                        cmd = ["pactl", "set-sink-volume", "@DEFAULT_SINK@", word]
                        msg = f"Set volume to {word}."
                        break
            
            if not cmd:
                # Default toggle or status check?
                return AgentResponse(agent=self.name, status="info", message="Volume control unclear. Try 'turn up' or 'mute'.")

            subprocess.run(cmd, check=True)
            return AgentResponse(agent=self.name, status="success", message=msg, payload={"action": "volume"})
            
        except Exception as e:
            logger.error("Volume control failed", error=str(e))
            return AgentResponse(agent=self.name, status="error", message="Failed to adjust volume.", payload={"error": str(e)})

    async def _handle_playback(self, text: str) -> AgentResponse:
        action = ""
        msg = ""
        
        if "play" in text or "resume" in text:
            action = "play"
            msg = "Resuming playback."
        elif "pause" in text or "stop" in text:
            action = "pause"
            msg = "Paused playback."
        elif "next" in text or "skip" in text:
            action = "next"
            msg = "Skipping track."
        elif "previous" in text or "back" in text:
            action = "previous"
            msg = "Previous track."
            
        if not action:
            return AgentResponse(agent=self.name, status="unhandled", message="Unknown media command.")

        try:
            subprocess.run(["playerctl", action], check=True)
            return AgentResponse(
                agent=self.name, 
                status="success", 
                message=msg, 
                payload={"action": action}
            )
        except subprocess.CalledProcessError:
             return AgentResponse(
                 agent=self.name,
                 status="warning",
                 message="No active media player found to control.",
                 payload={"error": "no_player"}
             )
