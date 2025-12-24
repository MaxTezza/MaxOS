import asyncio
import os
from typing import Any

import anthropic
import openai
import structlog


class LLMAPI:
    def __init__(
        self,
        timeout_seconds: int = 10,
        retry_attempts: int = 3,
        temperature: float = 0.1,
        max_tokens: int = 500,
    ):
        self.anthropic_client: anthropic.Anthropic | None = None
        self.openai_client: openai.OpenAI | None = None
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = structlog.get_logger("max_os.llm_api")

        # Initialize Anthropic client if API key is available
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
            self.logger.info("Anthropic client initialized")

        # Initialize OpenAI client if API key is available
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if openai_api_key:
            self.openai_client = openai.OpenAI(api_key=openai_api_key)
            self.logger.info("OpenAI client initialized")

    async def generate_text(
        self,
        prompt: str,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """
        Generate text using LLM API with timeout and retry logic.
        
        Args:
            prompt: Input prompt for the LLM
            model: Model identifier (defaults to Claude)
            max_tokens: Maximum tokens to generate (overrides instance default)
            temperature: Temperature for generation (overrides instance default)
            
        Returns:
            Generated text response
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        
        for attempt in range(self.retry_attempts):
            try:
                # Try with timeout
                response = await asyncio.wait_for(
                    self._generate_text_internal(prompt, model, max_tokens, temperature),
                    timeout=self.timeout_seconds
                )
                return response
            except asyncio.TimeoutError:
                self.logger.warning(
                    "LLM API timeout",
                    extra={"attempt": attempt + 1, "timeout": self.timeout_seconds}
                )
                if attempt == self.retry_attempts - 1:
                    raise
            except Exception as e:
                self.logger.error("LLM API error", extra={"error": str(e), "attempt": attempt + 1})
                if attempt == self.retry_attempts - 1:
                    raise
        
        return "Failed to generate response after retries."

    async def _generate_text_internal(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Internal method to call LLM API."""
        if self.anthropic_client:
            try:
                # Run synchronous Anthropic client in thread pool
                message = await asyncio.to_thread(
                    self.anthropic_client.messages.create,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                self.logger.debug("Anthropic API call successful", extra={"model": model})
                return message.content[0].text
            except Exception as e:
                self.logger.error(f"Anthropic API error: {e}")
                # Fallback to OpenAI if Anthropic fails

        if self.openai_client:
            try:
                # Run synchronous OpenAI client in thread pool
                chat_completion = await asyncio.to_thread(
                    self.openai_client.chat.completions.create,
                    messages=[{"role": "user", "content": prompt}],
                    model="gpt-4o",
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                self.logger.debug("OpenAI API call successful", extra={"model": "gpt-4o"})
                return chat_completion.choices[0].message.content
            except Exception as e:
                self.logger.error(f"OpenAI API error: {e}")

        raise RuntimeError("No LLM client available or all API calls failed")

    def is_available(self) -> bool:
        """Check if any LLM client is available."""
        return self.anthropic_client is not None or self.openai_client is not None
