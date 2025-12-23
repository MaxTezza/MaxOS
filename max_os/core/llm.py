"""LLM adapter with graceful fallback when API keys are missing."""

from __future__ import annotations

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

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider == "anthropic" and self._has_anthropic():
            return self._run_anthropic(system_prompt, user_prompt)
        if self.provider == "openai" and self._has_openai():
            return self._run_openai(system_prompt, user_prompt)
        return self._stub_completion(system_prompt, user_prompt)

    def _has_anthropic(self) -> bool:
        return bool(
            self.settings.llm.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")
        )

    def _has_openai(self) -> bool:
        return bool(self.settings.llm.get("openai_api_key") or os.environ.get("OPENAI_API_KEY"))

    def _run_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        if Anthropic is None:
            raise RuntimeError("anthropic package not installed")
        client = Anthropic(
            api_key=self.settings.llm.get("anthropic_api_key")
            or os.environ.get("ANTHROPIC_API_KEY")
        )
        message = client.messages.create(
            model=self.model,
            max_tokens=256,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text  # type: ignore[index]

    def _run_openai(self, system_prompt: str, user_prompt: str) -> str:
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
            max_tokens=256,
        )
        return completion.choices[0].message.content or ""

    def _stub_completion(self, system_prompt: str, user_prompt: str) -> str:
        return f"[stub-response] {user_prompt[:120]}"
