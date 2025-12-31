"""
MaxOS V2 Main Runner.
Integrates Senses (Voice/Video), Orchestrator (Brains), and Anticipation Engine.
"""

import asyncio
import signal
import sys
from typing import NoReturn

import structlog

from max_os.core.orchestrator import AIOperatingSystem
from max_os.core.senses import Senses

logger = structlog.get_logger("max_os.runner")

class MaxOSRunner:
    def __init__(self):
        self.orchestrator = AIOperatingSystem()
        self.senses = Senses(wake_word="max")
        self.running = False

    async def start(self) -> None:
        """Main Event Loop"""
        self.running = True
        
        # 1. Start Senses (Background Threads)
        try:
            self.senses.start()
        except Exception as e:
            logger.error("Failed to start senses (is microphone connected?)", error=str(e))
            # Continue anyway, CLI might work
        
        logger.info("MaxOS V2 Online. Waiting for input...", wake_word=self.senses.wake_word)
        print(f"👂 Listening for '{self.senses.wake_word}'...")

        # 2. Main Loop
        while self.running:
            # A. Check Voice Commands
            command = self.senses.get_next_command()
            if command:
                await self._handle_input(command, source="voice")
                
            # B. Check Vision (Optional / Future)
            # frame = self.senses.get_current_frame()
            # if frame: ...

            # C. Check Anticipation (Proactive)
            # Run every ~10 seconds or check elapsed time
            # For this MVP loop, we check every iteration but limit inside logic/rate-limiting
            try:
                # Mock context for now. In real system, we'd gather from self.orchestrator._gather_context_signals
                context_signals = {"time": "now"} 
                suggestion = await self.orchestrator.check_for_proactive_events(context_signals)
                if suggestion:
                    self._speak(suggestion)
            except Exception as e:
                logger.error("Anticipation error", error=str(e))

            # Sleep briefly to yield to event loop
            await asyncio.sleep(0.1)

    async def _handle_input(self, text: str, source: str = "text") -> None:
        logger.info(f"Processing {source} input: {text}")
        print(f"User ({source}): {text}")
        
        response = await self.orchestrator.handle_text(text)
        
        # Speak or Print Response
        self._speak(response.message)

    def _speak(self, text: str) -> None:
        """Output layer. Currently Prints, future: Google TTS."""
        print(f"\nExample Voice: 🗣️ '{text}'\n")
        # TODO: Integrate gTTS or Google Cloud TTS here
        
    def stop(self) -> None:
        logger.info("Shutting down MaxOS...")
        self.running = False
        self.senses.stop()


async def main():
    runner = MaxOSRunner()
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        runner.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    
    await runner.start()

if __name__ == "__main__":
    asyncio.run(main())
