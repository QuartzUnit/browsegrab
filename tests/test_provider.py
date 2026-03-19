"""Tests for browsegrab.llm.provider module."""

from __future__ import annotations

import pytest

from browsegrab.config import LLMConfig
from browsegrab.llm.provider import (
    OllamaProvider,
    OpenAICompatProvider,
    VLLMProvider,
    get_provider,
)

# ── get_provider() factory ────────────────────────────────────


class TestGetProvider:
    def test_vllm_provider(self):
        config = LLMConfig(provider="vllm", base_url="http://localhost:30000/v1", model="test-model")
        provider = get_provider(config)

        assert isinstance(provider, VLLMProvider)

    def test_ollama_provider(self):
        config = LLMConfig(provider="ollama", base_url="http://localhost:11434", model="llama3:8b")
        provider = get_provider(config)

        assert isinstance(provider, OllamaProvider)

    def test_openai_provider(self):
        config = LLMConfig(provider="openai", base_url="http://api.example.com/v1", model="gpt-4")
        provider = get_provider(config)

        assert isinstance(provider, OpenAICompatProvider)

    def test_unknown_provider_raises(self):
        config = LLMConfig()
        # Override the type-checked field directly
        object.__setattr__(config, "provider", "unknown_backend")

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_provider(config)

    def test_default_config_returns_vllm(self):
        """get_provider() with no args should return VLLMProvider (default config)."""
        provider = get_provider()
        assert isinstance(provider, VLLMProvider)


# ── VLLMProvider properties ───────────────────────────────────


class TestVLLMProvider:
    def test_name(self):
        p = VLLMProvider()
        assert p.name == "vllm"

    def test_model(self):
        p = VLLMProvider(model="my-model")
        assert p.model == "my-model"

    def test_default_model(self):
        p = VLLMProvider()
        assert p.model == "Qwen/Qwen3.5-32B-AWQ"


# ── OllamaProvider properties ────────────────────────────────


class TestOllamaProvider:
    def test_name(self):
        p = OllamaProvider()
        assert p.name == "ollama"

    def test_model(self):
        p = OllamaProvider(model="codellama:13b")
        assert p.model == "codellama:13b"

    def test_default_model(self):
        p = OllamaProvider()
        assert p.model == "qwen2.5:14b"


# ── OpenAICompatProvider properties ──────────────────────────


class TestOpenAICompatProvider:
    def test_name(self):
        p = OpenAICompatProvider()
        assert p.name == "openai"

    def test_model(self):
        p = OpenAICompatProvider(model="gpt-4o")
        assert p.model == "gpt-4o"
