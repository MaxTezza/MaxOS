"""Planning agent specializing in creating plans and roadmaps."""

from max_os.agents.base_specialized_agent import SpecializedAgent


class PlanningAgent(SpecializedAgent):
    """Agent specialized in planning and roadmap creation."""

    def __init__(self, llm):
        """Initialize planning agent.
        
        Args:
            llm: GeminiClient instance
        """
        super().__init__(
            llm=llm,
            role="planning",
            expertise="Creating detailed plans, roadmaps, and schedules",
        )
