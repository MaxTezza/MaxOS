from max_os.agents.base import BaseAgent


class AgentRegistry:
    """A simple registry for agent instances."""

    def __init__(self):
        self._registry: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent):
        """Registers an agent instance."""
        self._registry[agent.name] = agent

    def get(self, agent_name: str) -> BaseAgent | None:
        """Gets an agent instance by name."""
        return self._registry.get(agent_name)

    def get_all(self) -> dict[str, BaseAgent]:
        """Gets all registered agent instances."""
        return self._registry

AGENT_REGISTRY = AgentRegistry()
