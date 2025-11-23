from pathlib import Path

from max_os.agents.base import AgentResponse
from max_os.core.memory import ConversationMemory


def test_memory_retains_limit():
    memory = ConversationMemory(limit=2)
    memory.add_user("first")
    memory.add_user("second")
    memory.add_user("third")
    assert len(memory.history) == 2
    assert memory.history[0].content == "second"


def test_memory_add_agent():
    memory = ConversationMemory(limit=5)
    response = AgentResponse(agent="filesystem", status="planned", message="Done")
    memory.add_agent(response)
    assert memory.history[-1].content.startswith("filesystem")


def test_memory_dump(tmp_path: Path):
    memory = ConversationMemory(limit=5)
    memory.add_user("hello")
    dest = tmp_path / "transcript.txt"
    memory.dump(dest)
    assert "hello" in dest.read_text()
