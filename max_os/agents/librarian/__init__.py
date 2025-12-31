"""
The Librarian Agent.
Watches specific directories (e.g. ~/Downloads) and organizes files automatically.
"""

import os
import time
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

import structlog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from max_os.agents.base import AgentRequest, AgentResponse, BaseAgent

logger = structlog.get_logger("max_os.agents.librarian")

class OrganizationHandler(FileSystemEventHandler):
    """Handles file system events for the Librarian."""
    
    def __init__(self, agent):
        self.agent = agent

    def on_created(self, event):
        if event.is_directory:
            return
        
        # We need to run the async processing in the main loop
        # Since watchdog runs in a thread, we use run_coroutine_threadsafe or just trigger a callback
        # For simplicity in this architecture, we'll queue it or just log it for now
        # Ideally, we push to an asyncio queue that the main agent loop consumes.
        logger.info(f"New file detected: {event.src_path}")
        self.agent.process_queue.put_nowait(event.src_path)


class LibrarianAgent(BaseAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.name = "librarian"
        self.description = "Organizes files and watches directories."
        self.watch_path = Path(os.path.expanduser("~/Downloads"))
        
        # Async Queue for processing files
        self.process_queue = asyncio.Queue()
        
        # Watchdog setup
        self.observer = Observer()
        self.handler = OrganizationHandler(self)
        self.watching = False

    async def start(self):
        """Starts the filesystem watcher."""
        if not self.watch_path.exists():
            logger.warning(f"Watch path {self.watch_path} does not exist. Creating it.")
            self.watch_path.mkdir(parents=True, exist_ok=True)
            
        self.observer.schedule(self.handler, str(self.watch_path), recursive=False)
        self.observer.start()
        self.watching = True
        logger.info(f"Librarian watching: {self.watch_path}")
        
        # Start the processing loop as a background task
        asyncio.create_task(self._processing_loop())

    async def stop(self):
        if self.watching:
            self.observer.stop()
            self.observer.join()
            self.watching = False

    async def _processing_loop(self):
        """Continually processes files from the queue."""
        while True:
            file_path_str = await self.process_queue.get()
            try:
                await self._organize_file(Path(file_path_str))
            except Exception as e:
                logger.error(f"Failed to organize {file_path_str}", error=str(e))
            finally:
                self.process_queue.task_done()

    async def _organize_file(self, file_path: Path):
        """Decides where a file should go and moves it."""
        # Wait for file write to complete (debounce)
        await asyncio.sleep(2)
        
        if not file_path.exists():
            return

        filename = file_path.name
        ext = file_path.suffix.lower()
        
        # Simple Rules for now (Phase 1)
        # Phase 2: Use LLM to classify "Invoice_2024.pdf" vs "Readinglist.pdf"
        destination = None
        
        if ext in [".jpg", ".png", ".gif", ".jpeg", ".webp"]:
            destination = Path(os.path.expanduser("~/Pictures"))
        elif ext in [".pdf", ".docx", ".txt", ".md"]:
            destination = Path(os.path.expanduser("~/Documents"))
        elif ext in [".mp3", ".wav", ".flac"]:
            destination = Path(os.path.expanduser("~/Music"))
        elif ext in [".zip", ".tar", ".gz", ".deb"]:
            destination = Path(os.path.expanduser("~/Downloads/Installers"))
        
        if destination:
            destination.mkdir(parents=True, exist_ok=True)
            new_path = destination / filename
            
            # Handle duplicates
            if new_path.exists():
                timestamp = int(time.time())
                new_path = destination / f"{file_path.stem}_{timestamp}{ext}"
            
            shutil.move(str(file_path), str(new_path))
            logger.info("Librarian organized file", src=str(file_path), dst=str(new_path))

    def can_handle(self, request: AgentRequest) -> bool:
        return "organize" in request.text.lower() or "clean up" in request.text.lower()

    async def handle(self, request: AgentRequest) -> AgentResponse:
        # Manual trigger
        if "downloads" in request.text.lower():
            count = 0
            # Manually scan directory
            for item in self.watch_path.glob("*"):
                if item.is_file():
                    await self._organize_file(item)
                    count += 1
            return AgentResponse(agent=self.name, status="success", message=f"Organized {count} files in Downloads.")
            
        return AgentResponse(agent=self.name, status="unhandled", message="I can only organize your Downloads folder right now.")
