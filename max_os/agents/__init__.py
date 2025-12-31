from max_os.core.registry import AGENT_REGISTRY

from .agent_evolver import AgentEvolverAgent
from .app_launcher import AppLauncherAgent
from .base import AgentRequest, AgentResponse, BaseAgent
from .browser import BrowserAgent
from .developer import DeveloperAgent
from .filesystem import FileSystemAgent
from .home_automation import HomeAutomationAgent
from .knowledge import KnowledgeAgent
from .librarian import LibrarianAgent
from .media import MediaAgent
from .network import NetworkAgent
from .scheduler import SchedulerAgent
from .system import SystemAgent
from .watchman import WatchmanAgent

__all__ = [
    "BaseAgent",
    "AgentRequest",
    "AgentResponse",
    "AppLauncherAgent",
    "BrowserAgent",
    "DeveloperAgent",
    "FileSystemAgent",
    "HomeAutomationAgent",
    "KnowledgeAgent",
    "LibrarianAgent",
    "MediaAgent",
    "NetworkAgent",
    "SchedulerAgent",
    "SystemAgent",
    "WatchmanAgent",
    "AgentEvolverAgent",
    "AGENT_REGISTRY",
]
