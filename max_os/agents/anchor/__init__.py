from max_os.core.agent import BaseAgent
from max_os.core.llm import LLMProvider
import feedparser
import structlog
from typing import Optional

logger = structlog.get_logger("max_os.agents.anchor")

class AnchorAgent(BaseAgent):
    def __init__(self, llm: LLMProvider):
        super().__init__(llm)
        self.name = "Anchor"
        self.description = "Delivers news briefings from RSS feeds."
        # Default reputable sources
        self.feeds = {
            "tech": "http://feeds.feedburner.com/TechCrunch/",
            "world": "http://feeds.bbci.co.uk/news/world/rss.xml",
            "science": "https://www.sciencedaily.com/rss/top/science.xml"
        }

    def can_handle(self, user_input: str) -> bool:
        keywords = ["news", "headlines", "briefing", "what's happening", "world", "tech"]
        return any(k in user_input.lower() for k in keywords)

    async def execute(self, user_input: str, context: Optional[str] = None) -> str:
        logger.info(f"Processing news request: {user_input}")
        
        # Determine category
        category = "world"
        if "tech" in user_input.lower(): category = "tech"
        if "science" in user_input.lower(): category = "science"
        
        url = self.feeds.get(category, self.feeds["world"])
        
        try:
            feed = feedparser.parse(url)
            # Get top 3 headlines
            headlines = [entry.title for entry in feed.entries[:3]]
            
            summary = "\n".join(f"- {h}" for h in headlines)
            
            return await self.llm.generate(
                system_prompt=f"You are a news anchor. Summarize these headlines briefly and professionally:\n{summary}",
                user_prompt=user_input
            )
        except Exception as e:
            logger.error("News fetch failed", error=str(e))
            return "The teletype is down. I can't reach the news wire."
