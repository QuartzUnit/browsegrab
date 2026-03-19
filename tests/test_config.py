"""Tests for browsegrab.config module."""

from __future__ import annotations

import pytest

from browsegrab.config import (
    AgentConfig,
    BrowseGrabConfig,
    BrowserConfig,
    LLMConfig,
    SnapshotConfig,
)

# ── BrowserConfig ──────────────────────────────────────────────


class TestBrowserConfigDefaults:
    def test_headless_default(self):
        cfg = BrowserConfig()
        assert cfg.headless is True

    def test_timeout_ms_default(self):
        cfg = BrowserConfig()
        assert cfg.timeout_ms == 30_000

    def test_viewport_defaults(self):
        cfg = BrowserConfig()
        assert cfg.viewport_width == 1280
        assert cfg.viewport_height == 720

    def test_user_agent_default_none(self):
        cfg = BrowserConfig()
        assert cfg.user_agent is None

    def test_locale_default(self):
        cfg = BrowserConfig()
        assert cfg.locale == "en-US"

    def test_ignore_https_errors_default(self):
        cfg = BrowserConfig()
        assert cfg.ignore_https_errors is False


class TestBrowserConfigFromEnv:
    def test_from_env_defaults(self, monkeypatch):
        """With no env vars set, from_env() should return defaults."""
        # Clear any vars that might be set
        for _key in list(monkeypatch._env_keys if hasattr(monkeypatch, '_env_keys') else []):
            pass
        monkeypatch.delenv("BROWSEGRAB_BROWSER_HEADLESS", raising=False)
        monkeypatch.delenv("BROWSEGRAB_BROWSER_TIMEOUT_MS", raising=False)
        monkeypatch.delenv("BROWSEGRAB_BROWSER_VIEWPORT_WIDTH", raising=False)
        monkeypatch.delenv("BROWSEGRAB_BROWSER_VIEWPORT_HEIGHT", raising=False)
        monkeypatch.delenv("BROWSEGRAB_BROWSER_USER_AGENT", raising=False)
        monkeypatch.delenv("BROWSEGRAB_BROWSER_LOCALE", raising=False)
        monkeypatch.delenv("BROWSEGRAB_BROWSER_IGNORE_HTTPS_ERRORS", raising=False)
        cfg = BrowserConfig.from_env()
        assert cfg.headless is True
        assert cfg.timeout_ms == 30_000
        assert cfg.user_agent is None

    def test_from_env_custom_values(self, monkeypatch):
        monkeypatch.setenv("BROWSEGRAB_BROWSER_HEADLESS", "false")
        monkeypatch.setenv("BROWSEGRAB_BROWSER_TIMEOUT_MS", "60000")
        monkeypatch.setenv("BROWSEGRAB_BROWSER_VIEWPORT_WIDTH", "1920")
        monkeypatch.setenv("BROWSEGRAB_BROWSER_VIEWPORT_HEIGHT", "1080")
        monkeypatch.setenv("BROWSEGRAB_BROWSER_USER_AGENT", "TestBot/1.0")
        monkeypatch.setenv("BROWSEGRAB_BROWSER_LOCALE", "ko-KR")
        monkeypatch.setenv("BROWSEGRAB_BROWSER_IGNORE_HTTPS_ERRORS", "true")
        cfg = BrowserConfig.from_env()
        assert cfg.headless is False
        assert cfg.timeout_ms == 60_000
        assert cfg.viewport_width == 1920
        assert cfg.viewport_height == 1080
        assert cfg.user_agent == "TestBot/1.0"
        assert cfg.locale == "ko-KR"
        assert cfg.ignore_https_errors is True


# ── LLMConfig ──────────────────────────────────────────────────


class TestLLMConfigDefaults:
    def test_defaults(self):
        cfg = LLMConfig()
        assert cfg.provider == "vllm"
        assert cfg.base_url == "http://localhost:30000/v1"
        assert cfg.model == "Qwen/Qwen3.5-32B-AWQ"
        assert cfg.api_key is None
        assert cfg.timeout_s == 60
        assert cfg.max_retries == 2
        assert cfg.temperature == 0.0
        assert cfg.max_tokens == 1024


class TestLLMConfigFromEnv:
    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("BROWSEGRAB_LLM_PROVIDER", "ollama")
        monkeypatch.setenv("BROWSEGRAB_LLM_BASE_URL", "http://localhost:11434/v1")
        monkeypatch.setenv("BROWSEGRAB_LLM_MODEL", "llama3:8b")
        monkeypatch.setenv("BROWSEGRAB_LLM_API_KEY", "sk-test-123")
        monkeypatch.setenv("BROWSEGRAB_LLM_TIMEOUT_S", "120")
        monkeypatch.setenv("BROWSEGRAB_LLM_MAX_RETRIES", "5")
        monkeypatch.setenv("BROWSEGRAB_LLM_TEMPERATURE", "0.7")
        monkeypatch.setenv("BROWSEGRAB_LLM_MAX_TOKENS", "2048")
        cfg = LLMConfig.from_env()
        assert cfg.provider == "ollama"
        assert cfg.base_url == "http://localhost:11434/v1"
        assert cfg.model == "llama3:8b"
        assert cfg.api_key == "sk-test-123"
        assert cfg.timeout_s == 120
        assert cfg.max_retries == 5
        assert cfg.temperature == pytest.approx(0.7)
        assert cfg.max_tokens == 2048


# ── SnapshotConfig ─────────────────────────────────────────────


class TestSnapshotConfigDefaults:
    def test_defaults(self):
        cfg = SnapshotConfig()
        assert cfg.max_snapshot_length == 5000
        assert cfg.max_content_length == 3000
        assert cfg.include_links is True
        assert cfg.filter_interactive_only is False


class TestSnapshotConfigFromEnv:
    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("BROWSEGRAB_SNAPSHOT_MAX_LENGTH", "8000")
        monkeypatch.setenv("BROWSEGRAB_SNAPSHOT_MAX_CONTENT_LENGTH", "4000")
        monkeypatch.setenv("BROWSEGRAB_SNAPSHOT_INCLUDE_LINKS", "false")
        monkeypatch.setenv("BROWSEGRAB_SNAPSHOT_INTERACTIVE_ONLY", "true")
        cfg = SnapshotConfig.from_env()
        assert cfg.max_snapshot_length == 8000
        assert cfg.max_content_length == 4000
        assert cfg.include_links is False
        assert cfg.filter_interactive_only is True


# ── AgentConfig ────────────────────────────────────────────────


class TestAgentConfigDefaults:
    def test_defaults(self):
        cfg = AgentConfig()
        assert cfg.max_steps == 10
        assert cfg.history_max_entries == 5
        assert cfg.cache_dir == "~/.cache/browsegrab"
        assert cfg.enable_cache is True
        assert cfg.loop_detection_window == 3


class TestAgentConfigFromEnv:
    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("BROWSEGRAB_AGENT_MAX_STEPS", "20")
        monkeypatch.setenv("BROWSEGRAB_AGENT_HISTORY_MAX", "10")
        monkeypatch.setenv("BROWSEGRAB_AGENT_CACHE_DIR", "/tmp/bg-cache")
        monkeypatch.setenv("BROWSEGRAB_AGENT_ENABLE_CACHE", "false")
        monkeypatch.setenv("BROWSEGRAB_AGENT_LOOP_WINDOW", "5")
        cfg = AgentConfig.from_env()
        assert cfg.max_steps == 20
        assert cfg.history_max_entries == 10
        assert cfg.cache_dir == "/tmp/bg-cache"
        assert cfg.enable_cache is False
        assert cfg.loop_detection_window == 5


# ── BrowseGrabConfig ──────────────────────────────────────────


class TestBrowseGrabConfig:
    def test_defaults_aggregation(self):
        cfg = BrowseGrabConfig()
        assert isinstance(cfg.browser, BrowserConfig)
        assert isinstance(cfg.llm, LLMConfig)
        assert isinstance(cfg.snapshot, SnapshotConfig)
        assert isinstance(cfg.agent, AgentConfig)
        # Verify sub-configs have their own defaults
        assert cfg.browser.headless is True
        assert cfg.llm.provider == "vllm"
        assert cfg.snapshot.max_snapshot_length == 5000
        assert cfg.agent.max_steps == 10

    def test_from_env_aggregates_all(self, monkeypatch):
        """from_env() should delegate to each sub-config's from_env()."""
        monkeypatch.setenv("BROWSEGRAB_BROWSER_HEADLESS", "false")
        monkeypatch.setenv("BROWSEGRAB_LLM_PROVIDER", "openai")
        monkeypatch.setenv("BROWSEGRAB_SNAPSHOT_MAX_LENGTH", "9999")
        monkeypatch.setenv("BROWSEGRAB_AGENT_MAX_STEPS", "50")
        cfg = BrowseGrabConfig.from_env()
        assert cfg.browser.headless is False
        assert cfg.llm.provider == "openai"
        assert cfg.snapshot.max_snapshot_length == 9999
        assert cfg.agent.max_steps == 50
