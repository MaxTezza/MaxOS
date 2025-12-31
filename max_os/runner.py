"""
MaxOS V2 Main Runner.
Integrates Senses (Voice/Video), Orchestrator (Brains), and Anticipation Engine.
"""

import asyncio
import signal
import sys
from typing import NoReturn

import signal
import sys
import asyncio
from typing import NoReturn

import structlog
import uvicorn

from max_os.core.orchestrator import AIOperatingSystem
from max_os.core.senses import Senses
from max_os.core.reflex import ReflexEngine
from max_os.core.voice import VoiceEngine
from max_os.interfaces.api.server import app, set_runner, broadcast_state_update

logger = structlog.get_logger("max_os.runner")

class MaxOSRunner:
    def __init__(self):
        self.orchestrator = AIOperatingSystem()
        self.senses = Senses(wake_word="max")
        self.reflex_engine = ReflexEngine()
        self.voice_engine = VoiceEngine()
        self.running = False
        
        # Link API
        set_runner(self)
        
        self.gui_process = None

    async def inject_command(self, text: str):
        """Allows external sources (API) to inject commands."""
        print(f"GUI Command: {text}")
        await self._handle_input(text, source="gui")

    async def start_api_server(self):
        """Runs the FastAPI server."""
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="error")
        server = uvicorn.Server(config)
        await server.serve()

    def start_gui(self):
        """Launches the React Frontend."""
        import subprocess
        import os
        
        # In Docker, we might already be serving the GUI or have it pre-built
        if os.environ.get("DOCKER_MODE") == "true":
            logger.info("Running in Docker Mode. Assuming GUI is built and served externally or pre-built.")
            return

        gui_path = "max_os/interfaces/gui"
        if os.path.exists(gui_path):
            logger.info("Launching Plasma Dashboard...")
            # Run npm run dev in background, silence output to keep console clean
            self.gui_process = subprocess.Popen(
                ["npm", "run", "dev", "--", "--host"], 
                cwd=gui_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            logger.warning("GUI directory not found. Skipping Frontend launch.")

    async def start(self) -> None:
        """Main Event Loop"""
        self.running = True
        
        # 0. Start API Server (Background)
        asyncio.create_task(self.start_api_server())
        
        # 0.5 Start GUI (Process)
        self.start_gui()
        
        # 1. Start Senses (Background Threads)
        try:
            self.senses.start()
        except Exception as e:
            logger.error("Failed to start senses (is microphone connected?)", error=str(e))
            # Continue anyway, CLI might work
            
        # 2. Start Agent Background Tasks (Librarian, etc.)
        await self.orchestrator.start_background_tasks()
        

        logger.info("MaxOS V2 Online. Waiting for input...", wake_word=self.senses.wake_word)
        print(f"👂 Listening for '{self.senses.wake_word}'...")
        print("💬 You can also type commands here (press Enter to send).")


        # 2. Main Loop
        asyncio.create_task(self._cli_loop())
        asyncio.create_task(self._health_broadcaster())

        while self.running:
            # A. Check Voice Commands
            command = self.senses.get_next_command()
            if command:
                await self._handle_input(command, source="voice")
                
            # B. Check Vision (Optional / Future)
            # frame = self.senses.get_current_frame()
            # if frame: ...

            # C. Check Anticipation (Proactive)
            try:
                context_signals = {"time": "now"} 
                suggestion = await self.orchestrator.check_for_proactive_events(context_signals)
                if suggestion:
                    self._speak(suggestion)
            except Exception as e:
                logger.error("Anticipation error", error=str(e))

            # Sleep briefly to yield to event loop
            await asyncio.sleep(0.1)

    async def _health_broadcaster(self):
        """Periodically sends system health to the GUI."""
        while self.running:
            try:
                health = self.orchestrator.system.get_system_health()
                await broadcast_state_update("system_health", health)
            except Exception as e:
                logger.error("Health broadcast error", error=str(e))
            await asyncio.sleep(5)

    async def _cli_loop(self):
        """CLI listener for terminal chat."""
        import aioconsole  # Try to use aioconsole for non-blocking input
        cli_enabled = True
        try:
            while self.running and cli_enabled:
                try:
                    line = await aioconsole.ainput("")
                    if line.strip():
                        await self._handle_input(line.strip(), source="chat")
                except EOFError:
                    break
        except ImportError:
            # Fallback to threaded input if aioconsole is not available
            logger.warning("aioconsole not found. Falling back to threaded CLI input.")
            while self.running:
                loop = asyncio.get_event_loop()
                line = await loop.run_in_executor(None, input, "")
                if line.strip():
                    await self._handle_input(line.strip(), source="chat")
        except Exception as e:
            logger.error("CLI loop error", error=str(e))

    async def _handle_input(self, text: str, source: str = "text") -> None:
        logger.info(f"Processing {source} input: {text}")
        print(f"User ({source}): {text}")
        
        # Broadcast to GUI
        await broadcast_state_update("transcript", {"role": "user", "text": text, "source": source})
        
        # 1. Check Reflexes (High Priority, Local)
        if self.reflex_engine.check_and_trigger(text):
            print("⚡ Reflex Executed.")
            await broadcast_state_update("reflex", {"triggered": True, "command": text})
            return

        # 2. Forward to Brain (Orchestrator)
        response = await self.orchestrator.handle_text(text)
        
        # Speak or Print Response
        self._speak(response.message)

    def _speak(self, text: str) -> None:
        """Output layer. Uses Google Cloud TTS."""
        print(f"\nExample Voice: 🗣️ '{text}'\n")
        
        # Broadcast to GUI
        asyncio.create_task(broadcast_state_update("transcript", {"role": "assistant", "text": text}))
        
        # Actual Audio (Blocking for now, to prevent self-listening logic issues)
        self.voice_engine.speak(text)
        
    def stop(self) -> None:
        logger.info("Shutting down MaxOS...")
        self.running = False
        self.senses.stop()
        
        if self.gui_process:
            self.gui_process.terminate()
            logger.info("GUI Shutdown.")


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
