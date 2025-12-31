from max_os.core.agent import BaseAgent
from max_os.core.llm import LLMProvider
import requests
import structlog
from typing import Optional

logger = structlog.get_logger("max_os.agents.meteorologist")

class MeteorologistAgent(BaseAgent):
    def __init__(self, llm: LLMProvider):
        super().__init__(llm)
        self.name = "Meteorologist"
        self.description = "Manages weather forecasts and environmental queries using wttr.in."

    def can_handle(self, user_input: str) -> bool:
        keywords = ["weather", "forecast", "rain", "temperature", "umbrella", "sun", "hot", "cold", "outside"]
        return any(k in user_input.lower() for k in keywords)

    async def execute(self, user_input: str, context: Optional[str] = None) -> str:
        logger.info(f"Processing weather request: {user_input}")
        
        # 1. Detect location (naive approach, future: use spacy or LLM)
        # Defaults to auto-detect by IP
        
        try:
            # 2. Call wttr.in (format j1 for JSON)
            # We will ask for current condition
            response = requests.get("https://wttr.in/?format=3")
            if response.status_code == 200:
                weather_data = response.text.strip()
                
                # 3. Interpret using LLM for personality
                return await self.llm.generate(
                    system_prompt=f"You are a helpful weather reporter. The current condition is: {weather_data}. Answer the user's specific question naturally.",
                    user_prompt=user_input
                )
            else:
                return "I'm having trouble connecting to the weather satellite."
        except Exception as e:
            logger.error("Weather check failed", error=str(e))
            return "I couldn't check the weather. Look out the window?"
