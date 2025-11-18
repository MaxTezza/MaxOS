from .base import BaseAgent, AgentRequest, AgentResponse
from .developer import DeveloperAgent
from .filesystem import FileSystemAgent
from .network import NetworkAgent
from .system import SystemAgent
from .agent_evolver import AgentEvolverAgent
from .knowledge import KnowledgeAgent
from max_os.core.registry import AGENT_REGISTRY

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
