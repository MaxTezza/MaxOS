from max_os.agents.base import AgentRequest, AgentResponse
from max_os.core.llm import LLMProvider
import wikipedia
import structlog

logger = structlog.get_logger("max_os.agents.scholar")

class ScholarAgent:
    name = "Scholar"
    description = "Retrieves definitions and summaries from Wikipedia."

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def can_handle(self, request: AgentRequest) -> bool:
        keywords = ["who is", "what is", "define", "history of", "wikipedia", "tell me about"]
        return any(k in request.text.lower() for k in keywords)

    async def handle(self, request: AgentRequest) -> AgentResponse:
        logger.info(f"Processing knowledge request: {request.text}")
        
        clean_input = request.text.lower()
        for phrase in ["who is ", "what is ", "define ", "tell me about "]:
            clean_input = clean_input.replace(phrase, "")
            
        try:
            summary = wikipedia.summary(clean_input, sentences=2)
            return AgentResponse(agent=self.name, status="success", message=f"{summary} (Source: Wikipedia)")
        except wikipedia.exceptions.DisambiguationError as e:
            return AgentResponse(agent=self.name, status="partial", message=f"That's broad. Did you mean {e.options[:3]}?")
        except wikipedia.exceptions.PageError:
            return AgentResponse(agent=self.name, status="error", message="I couldn't find a page for that in the library.")
        except Exception as e:
            logger.error("Wikipedia search failed", error=str(e))
            return AgentResponse(agent=self.name, status="error", message="The library is currently unavailable.")
