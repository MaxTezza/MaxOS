"""Google Gemini client for multi-agent system."""

from __future__ import annotations

import os
from typing import Any, Optional, Union

try:
    import google.generativeai as genai
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    genai = None  # type: ignore
    Image = None  # type: ignore


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

    async def process(
        self, text: Optional[str] = None, image: Optional[Any] = None
    ) -> str:
        """Process a prompt with optional image and return response.
        
        Args:
            text: Input text prompt
            image: Optional image (PIL Image, numpy array, or file path)
            
        Returns:
            Generated text response
        """
        # Build content list
        content = []
        
        if text:
            content.append(text)
        
        if image is not None:
            # Handle different image types
            if isinstance(image, str):
                # File path
                img = Image.open(image)
                content.append(img)
            elif hasattr(image, "shape"):  # numpy array
                # Convert numpy array to PIL Image
                import numpy as np
                if len(image.shape) == 3 and image.shape[2] == 3:
                    # BGR to RGB conversion for OpenCV images
                    image = image[:, :, ::-1]
                img = Image.fromarray(image.astype("uint8"))
                content.append(img)
            else:
                # Assume it's already a PIL Image
                content.append(image)
        
        if not content:
            raise ValueError("Either text or image must be provided")
        
        response = await self._model.generate_content_async(content)
        return response.text

    def process_sync(
        self, text: Optional[str] = None, image: Optional[Any] = None
    ) -> str:
        """Process a prompt with optional image synchronously.
        
        Args:
            text: Input text prompt
            image: Optional image (PIL Image, numpy array, or file path)
            
        Returns:
            Generated text response
        """
        # Build content list
        content = []
        
        if text:
            content.append(text)
        
        if image is not None:
            # Handle different image types
            if isinstance(image, str):
                # File path
                img = Image.open(image)
                content.append(img)
            elif hasattr(image, "shape"):  # numpy array
                # Convert numpy array to PIL Image
                import numpy as np
                if len(image.shape) == 3 and image.shape[2] == 3:
                    # BGR to RGB conversion for OpenCV images
                    image = image[:, :, ::-1]
                img = Image.fromarray(image.astype("uint8"))
                content.append(img)
            else:
                # Assume it's already a PIL Image
                content.append(image)
        
        if not content:
            raise ValueError("Either text or image must be provided")
        
        response = self._model.generate_content(content)
        return response.text
