"""Google Gemini API client with multimodal and 2M token context support."""

from __future__ import annotations

import asyncio
import os

import structlog

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    genai = None  # type: ignore
    GenerationConfig = None  # type: ignore
    Image = None  # type: ignore


class GeminiClient:
    """Client for Google Gemini API with multimodal support."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-1.5-pro",
        user_id: str | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.1,
        timeout_seconds: int = 30,
    ) -> None:
        """Initialize Gemini client.

        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            model: Model name (gemini-1.5-pro or gemini-1.5-flash)
            user_id: Optional user ID for context management
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation (0.0-1.0)
            timeout_seconds: Request timeout in seconds
        """
        if genai is None:
            raise RuntimeError("google-generativeai package not installed")

        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        if self.api_key:
            genai.configure(api_key=self.api_key)

        self.model_name = model
        self.user_id = user_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout_seconds
        self.logger = structlog.get_logger("max_os.gemini_client")

        # Initialize model
        self.model = genai.GenerativeModel(model_name=self.model_name) if self.api_key else None

        # Chat history for context management
        self.chat_history: list[dict[str, str]] = []

    async def process(
        self,
        text: str | None = None,
        image: str | Image.Image | None = None,
        audio: bytes | None = None,
        video: bytes | None = None,
        system_prompt: str | None = None,
        stream: bool = False,
    ) -> str:
        """Process multimodal input and return response.

        Args:
            text: Text input
            image: Image file path or PIL Image
            audio: Audio bytes
            video: Video bytes
            system_prompt: Optional system prompt
            stream: Whether to stream the response

        Returns:
            Generated text response

        Raises:
            RuntimeError: If API key not configured
            asyncio.TimeoutError: If request times out
        """
        if not self.api_key or not self.model:
            raise RuntimeError("Gemini API key not configured")

        # Build prompt parts
        parts = []

        if text:
            parts.append(text)

        if image:
            if isinstance(image, str):
                # Load image from path
                img = Image.open(image)
                parts.append(img)
            else:
                parts.append(image)

        if audio:
            # For audio, we need to upload it as a file
            parts.append({"mime_type": "audio/wav", "data": audio})

        if video:
            # For video, we need to upload it as a file
            parts.append({"mime_type": "video/mp4", "data": video})

        if not parts:
            raise ValueError("At least one input type (text, image, audio, video) required")

        # Generate response
        try:
            if system_prompt:
                # For system prompts, we need to use a chat session
                chat = self.model.start_chat(history=[])
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        chat.send_message,
                        parts,
                        generation_config=GenerationConfig(
                            max_output_tokens=self.max_tokens,
                            temperature=self.temperature,
                        ),
                    ),
                    timeout=self.timeout,
                )
            else:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.model.generate_content,
                        parts,
                        generation_config=GenerationConfig(
                            max_output_tokens=self.max_tokens,
                            temperature=self.temperature,
                        ),
                    ),
                    timeout=self.timeout,
                )

            result = response.text

            # Add to chat history
            if text:
                self.chat_history.append({"role": "user", "content": text})
                self.chat_history.append({"role": "assistant", "content": result})

            self.logger.info(
                "Gemini request successful",
                model=self.model_name,
                has_image=bool(image),
                has_audio=bool(audio),
                has_video=bool(video),
            )

            return result

        except asyncio.TimeoutError as e:
            self.logger.error("Gemini request timed out", timeout=self.timeout)
            raise asyncio.TimeoutError(f"Gemini request timed out after {self.timeout}s") from e
        except Exception as e:
            self.logger.error("Gemini request failed", error=str(e))
            raise RuntimeError(f"Gemini API error: {e}") from e

    async def generate_with_context(
        self,
        text: str,
        context: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate response with conversation context.

        Args:
            text: User input text
            context: Optional conversation history

        Returns:
            Generated text response
        """
        if not self.api_key or not self.model:
            raise RuntimeError("Gemini API key not configured")

        # Use provided context or stored chat history
        history = context or self.chat_history

        # Start a chat session with history
        chat = self.model.start_chat(
            history=[{"role": msg["role"], "parts": [msg["content"]]} for msg in history]
        )

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    chat.send_message,
                    text,
                    generation_config=GenerationConfig(
                        max_output_tokens=self.max_tokens,
                        temperature=self.temperature,
                    ),
                ),
                timeout=self.timeout,
            )

            result = response.text

            # Update chat history
            self.chat_history.append({"role": "user", "content": text})
            self.chat_history.append({"role": "model", "content": result})

            return result

        except asyncio.TimeoutError as e:
            self.logger.error("Gemini request timed out", timeout=self.timeout)
            raise asyncio.TimeoutError(f"Gemini request timed out after {self.timeout}s") from e
        except Exception as e:
            self.logger.error("Gemini request failed", error=str(e))
            raise RuntimeError(f"Gemini API error: {e}") from e

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.chat_history = []

    def get_history(self) -> list[dict[str, str]]:
        """Get conversation history."""
        return self.chat_history.copy()

    def process_sync(self, prompt: str) -> str:
        """Process a prompt synchronously.
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated text response
        """
        if not self.api_key or not self.model:
            raise RuntimeError("Gemini API key not configured")
        
        response = self.model.generate_content(prompt)
        return response.text
