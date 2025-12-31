from max_os.core.registry import AGENT_REGISTRY

from .agent_evolver import AgentEvolverAgent
from .app_launcher import AppLauncherAgent
from .base import AgentRequest, AgentResponse, BaseAgent
from .developer import DeveloperAgent
from .filesystem import FileSystemAgent
from .home_automation import HomeAutomationAgent
from .knowledge import KnowledgeAgent
from .media import MediaAgent
from .network import NetworkAgent
from .system import SystemAgent

__all__ = [
    "BaseAgent",
    "AgentRequest",
    "AgentResponse",
    "AppLauncherAgent",
    "DeveloperAgent",
    "FileSystemAgent",
    "HomeAutomationAgent",
    "MediaAgent",
    "NetworkAgent",
    "SystemAgent",
    "AgentEvolverAgent",
    "KnowledgeAgent",
    "AGENT_REGISTRY",
]
