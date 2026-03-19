"""Configuration dataclasses for browsegrab."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class BrowserConfig:
    """Playwright browser configuration."""

    headless: bool = True
    timeout_ms: int = 30_000
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: str | None = None
    locale: str = "en-US"
    ignore_https_errors: bool = False

    @classmethod
    def from_env(cls) -> BrowserConfig:
        """Load from BROWSEGRAB_BROWSER_* environment variables."""
        return cls(
            headless=os.environ.get("BROWSEGRAB_BROWSER_HEADLESS", "true").lower() == "true",
            timeout_ms=int(os.environ.get("BROWSEGRAB_BROWSER_TIMEOUT_MS", "30000")),
            viewport_width=int(os.environ.get("BROWSEGRAB_BROWSER_VIEWPORT_WIDTH", "1280")),
            viewport_height=int(os.environ.get("BROWSEGRAB_BROWSER_VIEWPORT_HEIGHT", "720")),
            user_agent=os.environ.get("BROWSEGRAB_BROWSER_USER_AGENT"),
            locale=os.environ.get("BROWSEGRAB_BROWSER_LOCALE", "en-US"),
            ignore_https_errors=os.environ.get("BROWSEGRAB_BROWSER_IGNORE_HTTPS_ERRORS", "false").lower() == "true",
        )


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: Literal["vllm", "ollama", "openai"] = "vllm"
    base_url: str = "http://localhost:30000/v1"
    model: str = "Qwen/Qwen3.5-32B-AWQ"
    api_key: str | None = None
    timeout_s: int = 60
    max_retries: int = 2
    temperature: float = 0.0
    max_tokens: int = 1024

    @classmethod
    def from_env(cls) -> LLMConfig:
        """Load from BROWSEGRAB_LLM_* environment variables."""
        return cls(
            provider=os.environ.get("BROWSEGRAB_LLM_PROVIDER", "vllm"),  # type: ignore[arg-type]
            base_url=os.environ.get("BROWSEGRAB_LLM_BASE_URL", "http://localhost:30000/v1"),
            model=os.environ.get("BROWSEGRAB_LLM_MODEL", "Qwen/Qwen3.5-32B-AWQ"),
            api_key=os.environ.get("BROWSEGRAB_LLM_API_KEY"),
            timeout_s=int(os.environ.get("BROWSEGRAB_LLM_TIMEOUT_S", "60")),
            max_retries=int(os.environ.get("BROWSEGRAB_LLM_MAX_RETRIES", "2")),
            temperature=float(os.environ.get("BROWSEGRAB_LLM_TEMPERATURE", "0.0")),
            max_tokens=int(os.environ.get("BROWSEGRAB_LLM_MAX_TOKENS", "1024")),
        )


@dataclass
class SnapshotConfig:
    """Snapshot and DOM compression configuration."""

    max_snapshot_length: int = 5000
    max_content_length: int = 3000
    include_links: bool = True
    filter_interactive_only: bool = False

    @classmethod
    def from_env(cls) -> SnapshotConfig:
        """Load from BROWSEGRAB_SNAPSHOT_* environment variables."""
        return cls(
            max_snapshot_length=int(os.environ.get("BROWSEGRAB_SNAPSHOT_MAX_LENGTH", "5000")),
            max_content_length=int(os.environ.get("BROWSEGRAB_SNAPSHOT_MAX_CONTENT_LENGTH", "3000")),
            include_links=os.environ.get("BROWSEGRAB_SNAPSHOT_INCLUDE_LINKS", "true").lower() == "true",
            filter_interactive_only=os.environ.get("BROWSEGRAB_SNAPSHOT_INTERACTIVE_ONLY", "false").lower() == "true",
        )


@dataclass
class AgentConfig:
    """Agent loop configuration."""

    max_steps: int = 10
    history_max_entries: int = 5
    cache_dir: str = "~/.cache/browsegrab"
    enable_cache: bool = True
    loop_detection_window: int = 3

    @classmethod
    def from_env(cls) -> AgentConfig:
        """Load from BROWSEGRAB_AGENT_* environment variables."""
        return cls(
            max_steps=int(os.environ.get("BROWSEGRAB_AGENT_MAX_STEPS", "10")),
            history_max_entries=int(os.environ.get("BROWSEGRAB_AGENT_HISTORY_MAX", "5")),
            cache_dir=os.environ.get("BROWSEGRAB_AGENT_CACHE_DIR", "~/.cache/browsegrab"),
            enable_cache=os.environ.get("BROWSEGRAB_AGENT_ENABLE_CACHE", "true").lower() == "true",
            loop_detection_window=int(os.environ.get("BROWSEGRAB_AGENT_LOOP_WINDOW", "3")),
        )


@dataclass
class BrowseGrabConfig:
    """Top-level configuration aggregating all subsystem configs."""

    browser: BrowserConfig = field(default_factory=BrowserConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    snapshot: SnapshotConfig = field(default_factory=SnapshotConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)

    @classmethod
    def from_env(cls) -> BrowseGrabConfig:
        """Load all configs from environment variables."""
        return cls(
            browser=BrowserConfig.from_env(),
            llm=LLMConfig.from_env(),
            snapshot=SnapshotConfig.from_env(),
            agent=AgentConfig.from_env(),
        )
