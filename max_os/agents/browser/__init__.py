"""
The Browser Agent.
Surfs the web so you don't have to.
Capabilities:
- Google Search
- Page Extraction (BeautifulSoup)
- Summarization (via LLM)
"""

import requests
from bs4 import BeautifulSoup
from googlesearch import search
from typing import List, Dict, Any, Optional
import structlog

from max_os.agents.base import AgentRequest, AgentResponse, BaseAgent

logger = structlog.get_logger("max_os.agents.browser")

class BrowserAgent(BaseAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.name = "browser"
        self.description = "Searches the internet and summarizes web pages."

    def can_handle(self, request: AgentRequest) -> bool:
        triggers = ["search", "google", "find out", "research", "browse", "look up"]
        return any(t in request.text.lower() for t in triggers) or request.intent.startswith("browser.")

    async def handle(self, request: AgentRequest) -> AgentResponse:
        text = request.text.lower()
        
        # 1. Simple Search
        # "Search for X", "Google X"
        query = self._extract_query(text)
        if not query:
             return AgentResponse(agent=self.name, status="error", message="What do you want me to search for?")
        
        logger.info("Browser searching", query=query)
        
        try:
            # Limit to 3 results for speed in this MVP
            results = list(search(query, num_results=3, advanced=True))
            
            # If user just wants links
            if "link" in text or "url" in text:
                 return self._format_results(results)
                 
            # If user wants research/summary (default)
            # Pick the first result that isn't a PDF/youtube and read it
            target_url = None
            for r in results:
                if not r.url.endswith(".pdf") and "youtube.com" not in r.url:
                    target_url = r.url
                    break
            
            if target_url:
                summary = self._read_and_summarize(target_url)
                return AgentResponse(
                    agent=self.name,
                    status="success",
                    message=f"Here is what I found on {target_url}:\n\n{summary}",
                    payload={"url": target_url, "summary": summary}
                )
            else:
                return self._format_results(results)

        except Exception as e:
            return AgentResponse(agent=self.name, status="error", message=f"Search failed: {str(e)}")

    def _extract_query(self, text: str) -> str:
        # Simple extraction
        for prefix in ["search for", "google", "research", "find out about", "look up"]:
            if prefix in text:
                return text.split(prefix, 1)[1].strip()
        return text

    def _format_results(self, results) -> AgentResponse:
        msg = "Here are the top results:\n"
        for i, r in enumerate(results):
             msg += f"{i+1}. {r.title} ({r.url})\n"
        return AgentResponse(agent=self.name, status="success", message=msg, payload={"results": [r.url for r in results]})

    def _read_and_summarize(self, url: str) -> str:
        """ Fetches URL and returns a summary (mock-summarized via text extraction for now). """
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.extract()
            
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Truncate for LLM (Mock summary for speed here, 
            # ideally we pass to Orchestrator's LLM to summarize properly)
            # For this MVP, we return the first 500 characters + "..."
            return clean_text[:800] + "...\n(Full content truncated)"
            
        except Exception as e:
            return f"Could not read page: {str(e)}"
