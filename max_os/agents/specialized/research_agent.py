"""Research agent specializing in finding factual information."""

from max_os.agents.base_specialized_agent import SpecializedAgent


class ResearchAgent(SpecializedAgent):
    """Agent specialized in research and fact-finding."""

    def __init__(self, llm):
        """Initialize research agent.
        
        Args:
            llm: GeminiClient instance
        """
        super().__init__(
            llm=llm,
            role="research",
            expertise="Finding factual information, data, and reliable sources",
        )
