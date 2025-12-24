"""LLM adapter with graceful fallback when API keys are missing."""

from __future__ import annotations

import asyncio
import os

from max_os.utils.config import Settings

try:
    from anthropic import Anthropic
except Exception:  # pragma: no cover - optional dependency
    Anthropic = None  # type: ignore

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore


class LLMClient:
    """Thin wrapper that abstracts provider differences."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider = settings.orchestrator.get("provider", "stub")
        self.model = settings.orchestrator.get("model", "claude-3-5-sonnet")
        self.max_tokens = settings.llm.get("max_tokens", 500)
        self.temperature = settings.llm.get("temperature", 0.1)
        self.timeout = settings.llm.get("timeout_seconds", 10)

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int | None = None) -> str:
        """Generate LLM response synchronously (deprecated, use generate_async).

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Optional override for max_tokens

        Returns:
            Generated text response
        """
        max_tokens = max_tokens or self.max_tokens
        if self.provider == "anthropic" and self._has_anthropic():
            return self._run_anthropic(system_prompt, user_prompt, max_tokens)
        if self.provider == "openai" and self._has_openai():
            return self._run_openai(system_prompt, user_prompt, max_tokens)
        return self._stub_completion(system_prompt, user_prompt)

    async def generate_async(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> str:
        """Generate LLM response asynchronously with timeout.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Optional override for max_tokens
            timeout: Timeout in seconds (default from settings)

        Returns:
            Generated text response

        Raises:
            asyncio.TimeoutError: If request exceeds timeout
        """
        timeout = timeout or self.timeout
        max_tokens = max_tokens or self.max_tokens

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self.generate, system_prompt, user_prompt, max_tokens),
                timeout=timeout,
            )
        except asyncio.TimeoutError as e:
            raise asyncio.TimeoutError(f"LLM request timed out after {timeout}s") from e

    def _has_anthropic(self) -> bool:
        return bool(
            self.settings.llm.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")
        )

    def _has_openai(self) -> bool:
        return bool(self.settings.llm.get("openai_api_key") or os.environ.get("OPENAI_API_KEY"))

    def _run_anthropic(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        if Anthropic is None:
            raise RuntimeError("anthropic package not installed")
        client = Anthropic(
            api_key=self.settings.llm.get("anthropic_api_key")
            or os.environ.get("ANTHROPIC_API_KEY")
        )
        message = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text  # type: ignore[index]

    def _run_openai(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        if OpenAI is None:
            raise RuntimeError("openai package not installed")
        client = OpenAI(
            api_key=self.settings.llm.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
        )
        completion = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=self.temperature,
        )
        return completion.choices[0].message.content or ""

    def _stub_completion(self, system_prompt: str, user_prompt: str) -> str:
        return f"[stub-response] {user_prompt[:120]}"
