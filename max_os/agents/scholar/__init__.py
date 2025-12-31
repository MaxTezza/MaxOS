from max_os.core.agent import BaseAgent
from max_os.core.llm import LLMProvider
import wikipedia
import structlog
from typing import Optional

logger = structlog.get_logger("max_os.agents.scholar")

class ScholarAgent(BaseAgent):
    def __init__(self, llm: LLMProvider):
        super().__init__(llm)
        self.name = "Scholar"
        self.description = "Retrieves definitions and summaries from Wikipedia."

    def can_handle(self, user_input: str) -> bool:
        keywords = ["who is", "what is", "define", "history of", "wikipedia", "tell me about"]
        return any(k in user_input.lower() for k in keywords)

    async def execute(self, user_input: str, context: Optional[str] = None) -> str:
        logger.info(f"Processing knowledge request: {user_input}")
        
        # 1. Extract query
        # Remove trigger phrases simply
        clean_input = user_input.lower()
        for phrase in ["who is ", "what is ", "define ", "tell me about "]:
            clean_input = clean_input.replace(phrase, "")
            
        try:
            # 2. Search Wikipedia
            # limit sentences to 2 for brevity
            summary = wikipedia.summary(clean_input, sentences=2)
            
            return f"{summary} (Source: Wikipedia)"
            
        except wikipedia.exceptions.DisambiguationError as e:
            return f"That's broad. Did you mean {e.options[:3]}?"
        except wikipedia.exceptions.PageError:
            return "I couldn't find a page for that in the library."
        except Exception as e:
            logger.error("Wikipedia search failed", error=str(e))
            return "The library is closed (Usage Limit potentially)."
