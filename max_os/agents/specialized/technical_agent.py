"""Technical agent specializing in technical analysis and implementation."""

from max_os.agents.base_specialized_agent import SpecializedAgent


class TechnicalAgent(SpecializedAgent):
    """Agent specialized in technical feasibility and implementation."""

    def __init__(self, llm):
        """Initialize technical agent.
        
        Args:
            llm: GeminiClient instance
        """
        super().__init__(
            llm=llm,
            role="technical",
            expertise="Analyzing technical feasibility and implementation details",
        )
