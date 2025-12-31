"""Google Gemini client for multi-agent system."""

from __future__ import annotations

import os
from typing import Any

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency
    genai = None  # type: ignore


class GeminiClient:
    """Simple Gemini client for multi-agent orchestration."""

    def __init__(
        self,
        model: str = "gemini-1.5-flash",
        api_key: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ):
        """Initialize Gemini client.
        
        Args:
            model: Model name (gemini-1.5-pro or gemini-1.5-flash)
            api_key: Google API key (or use GOOGLE_API_KEY env var)
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
        """
        if genai is None:
            raise RuntimeError(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai"
            )
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Configure API key
        api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        genai.configure(api_key=api_key)
        
        # Initialize model
        self._model = genai.GenerativeModel(
            model_name=self.model,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            },
        )

    async def process(self, prompt: str) -> str:
        """Process a prompt and return response.
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated text response
        """
        response = await self._model.generate_content_async(prompt)
        return response.text

    async def process_image(self, prompt: str, image: Any) -> str:
        """Process an image and text prompt together.
        
        Args:
            prompt: Text prompt
            image: PIL.Image object or image bytes
            
        Returns:
            Generated text response
        """
        response = await self._model.generate_content_async([prompt, image])
        return response.text

    def process_sync(self, prompt: str) -> str:
        """Process a prompt synchronously.
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated text response
        """
        response = self._model.generate_content(prompt)
        return response.text
