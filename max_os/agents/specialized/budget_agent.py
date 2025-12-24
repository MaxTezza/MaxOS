"""Budget agent specializing in financial analysis and cost estimation."""

from max_os.agents.base_specialized_agent import SpecializedAgent


class BudgetAgent(SpecializedAgent):
    """Agent specialized in financial analysis and budgeting."""

    def __init__(self, llm):
        """Initialize budget agent.
        
        Args:
            llm: GeminiClient instance
        """
        super().__init__(
            llm=llm,
            role="budget",
            expertise="Financial analysis, cost estimation, and budget planning",
        )
        # Use very low temperature for numerical accuracy
        self.llm.temperature = 0.0
