from max_os.agents.base import AgentRequest, AgentResponse
from max_os.core.llm import LLMProvider
import yfinance as yf
import structlog
import json

logger = structlog.get_logger("max_os.agents.broker")

class BrokerAgent:
    name = "Broker"
    description = "Provides real-time stock and crypto market data."

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def can_handle(self, request: AgentRequest) -> bool:
        keywords = ["stock", "price", "market", "bitcoin", "crypto", "share", "value", "ticker"]
        return any(k in request.text.lower() for k in keywords)

    async def handle(self, request: AgentRequest) -> AgentResponse:
        logger.info(f"Processing finance request: {request.text}")
        
        ticker_prompt = f"Extract the stock/crypto ticker symbol from this text. Return ONLY the symbol (e.g. AAPL, BTC-USD). If none, return INVALID.\nText: {request.text}"
        ticker = await self.llm.generate_async(system_prompt="You are a financial data extractor.", user_prompt=ticker_prompt)
        ticker = ticker.strip().upper()
        
        if ticker == "INVALID":
            return AgentResponse(agent=self.name, status="error", message="I couldn't identify the ticker symbol. Which stock or crypto?")

        try:
            stock = yf.Ticker(ticker)
            info = stock.fast_info
            price = info.last_price if hasattr(info, 'last_price') else "Unknown"
            
            return AgentResponse(
                agent=self.name, 
                status="success", 
                message=f"The current price of {ticker} is ${price:,.2f}."
            )
        except Exception as e:
            logger.error("Finance check failed", error=str(e))
            return AgentResponse(agent=self.name, status="error", message=f"I couldn't retrieve data for {ticker}.")
