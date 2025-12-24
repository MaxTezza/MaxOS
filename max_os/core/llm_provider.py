"""Multi-provider LLM system with fallback support."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from max_os.core.gemini_client import GeminiClient
from max_os.core.llm import LLMClient
from max_os.utils.config import Settings


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""

    name: str
    model: str
    priority: int
    enabled: bool = True


class LLMProvider:
    """Multi-provider LLM with automatic fallback."""

    def __init__(self, settings: Settings) -> None:
        """Initialize LLM provider.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = structlog.get_logger("max_os.llm_provider")

        # Configure providers based on settings
        self.providers = self._configure_providers()

        # Initialize clients
        self.gemini_client: GeminiClient | None = None
        self.llm_client = LLMClient(settings)

    def _configure_providers(self) -> list[ProviderConfig]:
        """Configure providers based on settings.

        Returns:
            List of provider configurations sorted by priority
        """
        providers = []

        # Check primary provider from settings
        primary_provider = self.settings.llm.get("provider", "gemini")

        # Add Gemini if configured
        if primary_provider == "gemini" or self.settings.llm.get("google_api_key"):
            providers.append(
                ProviderConfig(
                    name="gemini",
                    model=self.settings.llm.get("model", "gemini-1.5-pro"),
                    priority=1 if primary_provider == "gemini" else 2,
                )
            )

        # Add Anthropic if configured
        if primary_provider == "anthropic" or self.settings.llm.get("anthropic_api_key"):
            providers.append(
                ProviderConfig(
                    name="anthropic",
                    model=self.settings.orchestrator.get("model", "claude-3-5-sonnet"),
                    priority=1 if primary_provider == "anthropic" else 2,
                )
            )

        # Add OpenAI if configured
        if primary_provider == "openai" or self.settings.llm.get("openai_api_key"):
            providers.append(
                ProviderConfig(
                    name="openai",
                    model=self.settings.orchestrator.get("model", "gpt-4"),
                    priority=3,
                )
            )

        # Add stub provider as final fallback
        providers.append(
            ProviderConfig(
                name="stub",
                model="stub",
                priority=99,
            )
        )

        # Sort by priority
        return sorted(providers, key=lambda p: p.priority)

    def _get_gemini_client(self, user_id: str | None = None) -> GeminiClient:
        """Get or create Gemini client.

        Args:
            user_id: Optional user ID for context

        Returns:
            GeminiClient instance
        """
        if not self.gemini_client or self.gemini_client.user_id != user_id:
            self.gemini_client = GeminiClient(
                api_key=self.settings.llm.get("google_api_key"),
                model=self.settings.llm.get("model", "gemini-1.5-pro"),
                user_id=user_id,
                max_tokens=self.settings.llm.get("max_tokens", 8192),
                temperature=self.settings.llm.get("temperature", 0.1),
                timeout_seconds=self.settings.llm.get("timeout_seconds", 30),
            )
        return self.gemini_client

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        user_id: str | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> str:
        """Generate LLM response with automatic fallback.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            user_id: Optional user ID for context
            max_tokens: Optional max tokens override
            timeout: Optional timeout override

        Returns:
            Generated text response
        """
        last_error = None

        # Try each provider in order
        for provider in self.providers:
            if not provider.enabled:
                continue

            try:
                if provider.name == "gemini":
                    return await self._generate_gemini(
                        system_prompt, user_prompt, user_id, max_tokens, timeout
                    )
                elif provider.name in {"anthropic", "openai"}:
                    return await self._generate_legacy(
                        system_prompt, user_prompt, max_tokens, timeout
                    )
                elif provider.name == "stub":
                    return self.llm_client._stub_completion(system_prompt, user_prompt)

            except Exception as e:
                last_error = e
                self.logger.warning(
                    "Provider failed, trying next",
                    provider=provider.name,
                    error=str(e),
                )
                continue

        # All providers failed
        error_msg = f"All LLM providers failed. Last error: {last_error}"
        self.logger.error(error_msg)
        raise RuntimeError(error_msg)

    async def _generate_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        user_id: str | None,
        max_tokens: int | None,
        timeout: float | None,
    ) -> str:
        """Generate using Gemini.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            user_id: Optional user ID
            max_tokens: Optional max tokens
            timeout: Optional timeout

        Returns:
            Generated text
        """
        client = self._get_gemini_client(user_id)

        # Combine system prompt with user prompt
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"

        # Update client settings if overrides provided
        if max_tokens:
            client.max_tokens = max_tokens
        if timeout:
            client.timeout = int(timeout)

        response = await client.process(text=combined_prompt)

        self.logger.info("Gemini generation successful", user_id=user_id)
        return response

    async def _generate_legacy(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None,
        timeout: float | None,
    ) -> str:
        """Generate using legacy LLM client (Anthropic/OpenAI).

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Optional max tokens
            timeout: Optional timeout

        Returns:
            Generated text
        """
        return await self.llm_client.generate_async(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    async def generate_multimodal(
        self,
        text: str | None = None,
        image: str | Any | None = None,
        audio: bytes | None = None,
        video: bytes | None = None,
        system_prompt: str | None = None,
        user_id: str | None = None,
    ) -> str:
        """Generate response with multimodal inputs (Gemini only).

        Args:
            text: Text input
            image: Image file path or PIL Image
            audio: Audio bytes
            video: Video bytes
            system_prompt: Optional system prompt
            user_id: Optional user ID

        Returns:
            Generated text response

        Raises:
            RuntimeError: If Gemini not available
        """
        # Only Gemini supports multimodal
        client = self._get_gemini_client(user_id)

        return await client.process(
            text=text,
            image=image,
            audio=audio,
            video=video,
            system_prompt=system_prompt,
        )

    def get_active_provider(self) -> str:
        """Get the name of the active (highest priority enabled) provider.

        Returns:
            Provider name
        """
        for provider in self.providers:
            if provider.enabled:
                return provider.name
        return "none"
