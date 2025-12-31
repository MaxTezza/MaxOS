from max_os.core.agent import BaseAgent
from max_os.core.llm import LLMProvider
import yfinance as yf
import structlog
from typing import Optional

logger = structlog.get_logger("max_os.agents.broker")

class BrokerAgent(BaseAgent):
    def __init__(self, llm: LLMProvider):
        super().__init__(llm)
        self.name = "Broker"
        self.description = "Provides real-time stock and crypto market data."

    def can_handle(self, user_input: str) -> bool:
        keywords = ["stock", "price", "market", "bitcoin", "crypto", "share", "value", "ticker"]
        # Basic check, can be improved with regex
        return any(k in user_input.lower() for k in keywords)

    async def execute(self, user_input: str, context: Optional[str] = None) -> str:
        logger.info(f"Processing finance request: {user_input}")
        
        # 1. Extract ticker using LLM (simple extraction)
        ticker_prompt = f"Extract the stock/crypto ticker symbol from this text. Return ONLY the symbol (e.g. AAPL, BTC-USD). If none, return INVALID.\nText: {user_input}"
        ticker = await self.llm.generate(system_prompt="You are a financial data extractor.", user_prompt=ticker_prompt)
        ticker = ticker.strip().upper()
        
        if ticker == "INVALID":
            return "I couldn't identify the ticker symbol. Which stock or crypto?"

        try:
            # 2. Get Data
            stock = yf.Ticker(ticker)
            info = stock.fast_info
            
            # fast_info might miss some fields depending on asset type
            price = info.last_price if hasattr(info, 'last_price') else "Unknown"
            
            # 3. Format Response
            return f"The current price of {ticker} is ${price:,.2f}."
            
        except Exception as e:
            logger.error("Finance check failed", error=str(e))
            return f"I couldn't retrieve data for {ticker}. The market might be closed or the symbol is wrong."
