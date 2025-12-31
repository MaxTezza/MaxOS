from max_os.agents.base import AgentRequest, AgentResponse
from max_os.core.llm import LLMProvider
import feedparser
import structlog

logger = structlog.get_logger("max_os.agents.anchor")

class AnchorAgent:
    name = "Anchor"
    description = "Delivers news briefings from RSS feeds."

    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.feeds = {
            "tech": "http://feeds.feedburner.com/TechCrunch/",
            "world": "http://feeds.bbci.co.uk/news/world/rss.xml",
            "science": "https://www.sciencedaily.com/rss/top/science.xml"
        }

    def can_handle(self, request: AgentRequest) -> bool:
        keywords = ["news", "headlines", "briefing", "what's happening", "world", "tech"]
        return any(k in request.text.lower() for k in keywords)

    async def handle(self, request: AgentRequest) -> AgentResponse:
        logger.info(f"Processing news request: {request.text}")
        
        category = "world"
        if "tech" in request.text.lower(): category = "tech"
        if "science" in request.text.lower(): category = "science"
        
        url = self.feeds.get(category, self.feeds["world"])
        
        try:
            feed = feedparser.parse(url)
            headlines = [entry.title for entry in feed.entries[:3]]
            summary = "\n".join(f"- {h}" for h in headlines)
            
            message = await self.llm.generate_async(
                system_prompt=f"You are a news anchor. Summarize these headlines briefly and professionally:\n{summary}",
                user_prompt=request.text
            )
            return AgentResponse(agent=self.name, status="success", message=message)
        except Exception as e:
            logger.error("News fetch failed", error=str(e))
            return AgentResponse(agent=self.name, status="error", message="The teletype is down. I can't reach the news wire.")
