"""LLM provider implementations: vLLM, Ollama, OpenAI-compatible.

All providers use httpx directly — no SDK dependencies.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from browsegrab.config import LLMConfig
from browsegrab.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class VLLMProvider(LLMProvider):
    """vLLM OpenAI-compatible endpoint provider."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "Qwen/Qwen3.5-32B-AWQ",
        api_key: str | None = None,
        timeout_s: int = 60,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = timeout_s

    @property
    def name(self) -> str:
        return "vllm"

    @property
    def model(self) -> str:
        return self._model

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            # CRITICAL: disable reasoning parser — DGX restart may change default
            "chat_template_kwargs": {"enable_thinking": False},
        }
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return data["choices"][0]["message"]["content"]

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._base_url}/models")
                return resp.status_code == 200
        except Exception:
            return False


class OllamaProvider(LLMProvider):
    """Ollama API provider."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:14b",
        timeout_s: int = 60,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_s

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        return data["message"]["content"]

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


class OpenAICompatProvider(LLMProvider):
    """Generic OpenAI-compatible endpoint provider."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "gpt-4",
        api_key: str | None = None,
        timeout_s: int = 60,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = timeout_s

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return data["choices"][0]["message"]["content"]

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._base_url}/models")
                return resp.status_code == 200
        except Exception:
            return False


def get_provider(config: LLMConfig | None = None) -> LLMProvider:
    """Factory: create an LLM provider from config."""
    config = config or LLMConfig()
    if config.provider == "vllm":
        return VLLMProvider(
            base_url=config.base_url,
            model=config.model,
            api_key=config.api_key,
            timeout_s=config.timeout_s,
        )
    if config.provider == "ollama":
        return OllamaProvider(
            base_url=config.base_url,
            model=config.model,
            timeout_s=config.timeout_s,
        )
    if config.provider == "openai":
        return OpenAICompatProvider(
            base_url=config.base_url,
            model=config.model,
            api_key=config.api_key,
            timeout_s=config.timeout_s,
        )
    raise ValueError(f"Unknown LLM provider: {config.provider}")
