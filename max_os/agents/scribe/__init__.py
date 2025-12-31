import os
from max_os.agents.base import AgentRequest, AgentResponse
from max_os.core.llm import LLMProvider
import structlog
from pathlib import Path
from datetime import datetime

logger = structlog.get_logger("max_os.agents.scribe")

class ScribeAgent:
    name = "Scribe"
    description = "Manages personal notes in markdown format."

    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.notes_dir = Path.home() / "MaxOS_Notes"
        self.notes_dir.mkdir(exist_ok=True)

    def can_handle(self, request: AgentRequest) -> bool:
        keywords = ["note", "scribe", "remember", "write down", "journal", "diary"]
        return any(k in request.text.lower() for k in keywords)

    async def handle(self, request: AgentRequest) -> AgentResponse:
        logger.info(f"Processing note request: {request.text}")
        
        cleaned = request.text.lower()
        if any(w in cleaned for w in ["read", "show", "what are", "list"]):
            return AgentResponse(agent=self.name, status="success", message=self._list_notes())
        
        content_prompt = f"Extract the core content the user wants me to remember from this request. Return ONLY the content.\nRequest: {request.text}"
        content = await self.llm.generate_async(system_prompt="You are a meticulous scribe.", user_prompt=content_prompt)
        content = content.strip()
        
        if not content:
            return AgentResponse(agent=self.name, status="error", message="What would you like me to write down?")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"note_{timestamp}.md"
        filepath = self.notes_dir / filename
        
        try:
            with open(filepath, "w") as f:
                f.write(f"# Note - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{content}\n")
            return AgentResponse(agent=self.name, status="success", message=f"I've written that down in your notes folder as {filename}.")
        except Exception as e:
            logger.error("Failed to write note", error=str(e))
            return AgentResponse(agent=self.name, status="error", message="I couldn't reach my notebook right now.")

    def _list_notes(self) -> str:
        notes = sorted(self.notes_dir.glob("*.md"), reverse=True)
        if not notes:
             return "Your notebook is currently empty."
        
        summary = "Here are your recent notes:\n"
        for note in notes[:3]:
            with open(note, "r") as f:
                lines = f.readlines()
                preview = lines[2].strip() if len(lines) > 2 else "Empty"
                summary += f"- {note.name}: {preview[:50]}...\n"
        return summary
