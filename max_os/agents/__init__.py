from max_os.core.registry import AGENT_REGISTRY

from .agent_evolver import AgentEvolverAgent
from .base import AgentRequest, AgentResponse, BaseAgent
from .developer import DeveloperAgent
from .filesystem import FileSystemAgent
from .knowledge import KnowledgeAgent
from .network import NetworkAgent
from .system import SystemAgent

__all__ = [
    "BaseAgent",
    "AgentRequest",
    "AgentResponse",
    "DeveloperAgent",
    "FileSystemAgent",
    "NetworkAgent",
    "SystemAgent",
    "AgentEvolverAgent",
    "KnowledgeAgent",
    "AGENT_REGISTRY",
]
