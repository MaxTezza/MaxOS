import os
from max_os.core.agent import BaseAgent
from max_os.core.llm import LLMProvider
import structlog
from typing import Optional
from pathlib import Path
from datetime import datetime

logger = structlog.get_logger("max_os.agents.scribe")

class ScribeAgent(BaseAgent):
    def __init__(self, llm: LLMProvider):
        super().__init__(llm)
        self.name = "Scribe"
        self.description = "Manages personal notes in markdown format."
        self.notes_dir = Path.home() / "MaxOS_Notes"
        self.notes_dir.mkdir(exist_ok=True)

    def can_handle(self, user_input: str) -> bool:
        keywords = ["note", "scribe", "remember", "write down", "journal", "diary"]
        return any(k in user_input.lower() for k in keywords)

    async def execute(self, user_input: str, context: Optional[str] = None) -> str:
        logger.info(f"Processing note request: {user_input}")
        
        # 1. Decide action (Taking or Reading)
        cleaned = user_input.lower()
        if any(w in cleaned for w in ["read", "show", "what are", "list"]):
            return self._list_notes()
        
        # 2. Extract content for a new note
        content_prompt = f"Extract the core content the user wants me to remember from this request. Ignore the 'Max, remember' or 'take a note' parts. Return ONLY the content.\nRequest: {user_input}"
        content = await self.llm.generate(system_prompt="You are a meticulous scribe.", user_prompt=content_prompt)
        content = content.strip()
        
        if not content:
            return "What would you like me to write down?"

        # 3. Save note
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"note_{timestamp}.md"
        filepath = self.notes_dir / filename
        
        try:
            with open(filepath, "w") as f:
                f.write(f"# Note - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{content}\n")
            
            return f"I've written that down in your notes folder as {filename}."
        except Exception as e:
            logger.error("Failed to write note", error=str(e))
            return "I couldn't reach my notebook right now."

    def _list_notes(self) -> str:
        """List the last 3 notes for context."""
        notes = sorted(self.notes_dir.glob("*.md"), reverse=True)
        if not notes:
             return "Your notebook is currently empty."
        
        summary = "Here are your recent notes:\n"
        for note in notes[:3]:
            with open(note, "r") as f:
                # Get first 50 chars of content (skipping header)
                lines = f.readlines()
                preview = lines[2].strip() if len(lines) > 2 else "Empty"
                summary += f"- {note.name}: {preview[:50]}...\n"
        
        return summary
