"""
MaxOS Horizon Agent.
Provides visual perception by monitoring the screen.
"""

import asyncio
import base64
import io
import time
from typing import Dict, Any, Optional

import mss
from PIL import Image
import structlog

from max_os.agents.base import AgentRequest, AgentResponse, BaseAgent
from max_os.core.gemini_client import GeminiClient

logger = structlog.get_logger("max_os.agents.horizon")

class HorizonAgent(BaseAgent):
    name = "horizon"
    description = "Provides visual perception and screen awareness"
    
    def __init__(self, google_api_key: str):
        super().__init__()
        self.vision_client = GeminiClient(
            model="gemini-1.5-flash",
            api_key=google_api_key,
            temperature=0.1
        )
        self.last_capture_summary = "No visual data yet."
        self.last_capture_time = 0
        self.running = False
        self._loop_task = None

    def can_handle(self, request: AgentRequest) -> bool:
        keywords = ["see", "screen", "looking at", "on my monitor", "vision"]
        return any(k in request.text.lower() for k in keywords) or request.intent == "system.vision"

    async def start(self):
        """Starts the continuous vision loop."""
        if self.running:
            return
        self.running = True
        self._loop_task = asyncio.create_task(self._vision_loop())
        logger.info("Horizon Vision Loop started.")

    async def stop(self):
        self.running = False
        if self._loop_task:
            self._loop_task.cancel()
        logger.info("Horizon Vision Loop stopped.")

    async def handle(self, request: AgentRequest) -> AgentResponse:
        # Prompt for specific visual analysis
        if "what" in request.text.lower() or "tell me" in request.text.lower():
            try:
                img = self._capture_screen()
                analysis = await self.vision_client.process_image(
                    f"The user is asking: '{request.text}'. Based on this screenshot, provide a concise answer.",
                    img
                )
                return AgentResponse(
                    agent=self.name,
                    status="success",
                    message=analysis,
                    payload={"last_summary": self.last_capture_summary}
                )
            except Exception as e:
                logger.error("Vision handling error", error=str(e))
                return AgentResponse(
                    agent=self.name,
                    status="error",
                    message=f"I tried to see, but encountered an error: {str(e)}",
                    payload={}
                )
        
        return AgentResponse(
            agent=self.name,
            status="success",
            message=f"Last I saw: {self.last_capture_summary}",
            payload={"summary": self.last_capture_summary}
        )

    async def _vision_loop(self):
        """Background task to summarize screen every 30 seconds."""
        while self.running:
            try:
                img = self._capture_screen()
                summary = await self.vision_client.process_image(
                    "Provide a one-sentence summary of what is happening on this screen right now for an AI assistant's context.",
                    img
                )
                self.last_capture_summary = summary
                self.last_capture_time = time.time()
                logger.info("Screen summarized", summary=summary)
            except Exception as e:
                logger.error("Vision loop error", error=str(e))
            
            await asyncio.sleep(30) # Scan every 30 seconds to be resource-efficient

    def _capture_screen(self) -> Image.Image:
        """Captures the primary monitor."""
        with mss.mss() as sct:
            monitor = sct.monitors[1] # Primary monitor
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            # Downscale for efficiency and API limits if needed
            img.thumbnail((1280, 720))
            return img
