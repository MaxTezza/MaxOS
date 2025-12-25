"""Creative agent specializing in innovative ideas and solutions."""

from max_os.agents.base_specialized_agent import SpecializedAgent


class CreativeAgent(SpecializedAgent):
    """Agent specialized in creative thinking and innovation."""

    def __init__(self, llm):
        """Initialize creative agent.

        Args:
            llm: GeminiClient instance
        """
        super().__init__(
            llm=llm,
            role="creative",
            expertise="Generating innovative ideas and creative solutions",
        )
        # Use higher temperature for creativity
        self.llm.temperature = 0.8
