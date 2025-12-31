from max_os.agents.base import AgentRequest, AgentResponse
from max_os.core.llm import LLMProvider
import requests
import structlog

logger = structlog.get_logger("max_os.agents.meteorologist")

class MeteorologistAgent:
    name = "Meteorologist"
    description = "Manages weather forecasts and environmental queries using wttr.in."

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def can_handle(self, request: AgentRequest) -> bool:
        keywords = ["weather", "forecast", "rain", "temperature", "umbrella", "sun", "hot", "cold", "outside"]
        return any(k in request.text.lower() for k in keywords)

    async def handle(self, request: AgentRequest) -> AgentResponse:
        logger.info(f"Processing weather request: {request.text}")
        
        try:
            response = requests.get("https://wttr.in/?format=3")
            if response.status_code == 200:
                weather_data = response.text.strip()
                
                message = await self.llm.generate_async(
                    system_prompt=f"You are a helpful weather reporter. The current condition is: {weather_data}. Answer the user's specific question naturally.",
                    user_prompt=request.text
                )
                return AgentResponse(agent=self.name, status="success", message=message)
            else:
                return AgentResponse(agent=self.name, status="error", message="I'm having trouble connecting to the weather satellite.")
        except Exception as e:
            logger.error("Weather check failed", error=str(e))
            return AgentResponse(agent=self.name, status="error", message="I couldn't check the weather. Look out the window?")
