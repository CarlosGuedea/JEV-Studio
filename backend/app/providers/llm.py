"""LLM provider architecture.

LLMProvider abstracts chat-completions style models. The OpenAI-compatible
implementation covers OpenAI itself and any local server exposing the same
protocol (llama.cpp server, LM Studio, vLLM, …). Add new providers by
subclassing LLMProvider and registering them in registry().
"""
import os
from abc import ABC, abstractmethod
from typing import Any

import httpx

from ..config import get_settings


class LLMResult:
    def __init__(self, text: str, raw: dict[str, Any]) -> None:
        self.text = text
        self.raw = raw


class LLMProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def chat(self, *, model: str, system: str, prompt: str,
             temperature: float, max_tokens: int,
             endpoint: str | None = None, api_key: str | None = None) -> LLMResult:
        ...


class OpenAICompatibleProvider(LLMProvider):
    """Works with OpenAI and any OpenAI-compatible endpoint (llama.cpp, vLLM…)."""
    name = "openai_compatible"

    def chat(self, *, model: str, system: str, prompt: str,
             temperature: float, max_tokens: int,
             endpoint: str | None = None, api_key: str | None = None) -> LLMResult:
        settings = get_settings()
        base = (endpoint or settings.openai_base_url).rstrip("/")
        key = api_key or settings.openai_api_key
        if not key and "api.openai.com" in base:
            raise RuntimeError(
                "LLM node: set OPENAI_API_KEY in the environment "
                "(API keys are never stored inside workflows)."
            )
        payload: dict[str, Any] = {
            "model": model,
            "messages": (
                [{"role": "system", "content": system}] if system else []
            ) + [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            resp = client.post(f"{base}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            body = resp.text
        if len(body) > settings.llm_max_response_bytes:
            raise RuntimeError("LLM response exceeds the configured size limit")
        data = __import__("json").loads(body)
        text = data["choices"][0]["message"]["content"]
        return LLMResult(text=text, raw=data)


_PROVIDERS: dict[str, LLMProvider] = {}


def registry() -> dict[str, LLMProvider]:
    if not _PROVIDERS:
        p = OpenAICompatibleProvider()
        _PROVIDERS[p.name] = p
        _PROVIDERS["openai"] = p
        _PROVIDERS["llamacpp"] = p       # llama.cpp server is OpenAI-compatible
        _PROVIDERS["local"] = p          # local OpenAI-compatible servers
    return _PROVIDERS


def resolve_api_key(api_key_env: str) -> str | None:
    """Resolve the secret from the named environment variable at run time."""
    return os.environ.get(api_key_env) if api_key_env else None
