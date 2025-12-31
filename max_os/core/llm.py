"""LLM adapter with graceful fallback when API keys are missing."""

from __future__ import annotations

import asyncio
import os

from max_os.utils.config import Settings

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency
    genai = None  # type: ignore


class LLMClient:
    """Thin wrapper that abstracts provider differences."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider = settings.orchestrator.get("provider", "stub")
        self.model = settings.orchestrator.get("model", "gemini-1.5-pro")
        self.max_tokens = settings.llm.get("max_tokens", 500)
        self.temperature = settings.llm.get("temperature", 0.1)
        self.timeout = settings.llm.get("timeout_seconds", 10)

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int | None = None) -> str:
        """Generate LLM response synchronously (deprecated, use generate_async)."""
        max_tokens = max_tokens or self.max_tokens
        if self.provider == "google" and self._has_google():
            return self._run_google(system_prompt, user_prompt, max_tokens)
        return self._stub_completion(system_prompt, user_prompt)
    
    async def generate_async(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        max_tokens: int | None = None,
        timeout: float | None = None
    ) -> str:
        """Generate LLM response asynchronously with timeout."""
        timeout = timeout or self.timeout
        max_tokens = max_tokens or self.max_tokens
        
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self.generate, system_prompt, user_prompt, max_tokens
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError as e:
            raise asyncio.TimeoutError(f"LLM request timed out after {timeout}s") from e

    def _has_google(self) -> bool:
        return bool(self.settings.llm.get("google_api_key") or os.environ.get("GOOGLE_API_KEY"))

    def _run_google(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        """Run Google Gemini completion."""
        if genai is None:
            raise RuntimeError("google-generativeai package not installed")
        
        api_key = self.settings.llm.get("google_api_key") or os.environ.get("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel(
            model_name=self.model,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": max_tokens,
            },
        )
        
        # Combine system and user prompts for Gemini
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = model.generate_content(full_prompt)
        return response.text

    def _stub_completion(self, system_prompt: str, user_prompt: str) -> str:
        return f"[stub-response] {user_prompt[:120]}"
