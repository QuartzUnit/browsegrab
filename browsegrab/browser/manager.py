"""Playwright browser lifecycle management."""

from __future__ import annotations

import logging
from types import TracebackType

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from browsegrab.config import BrowserConfig

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Playwright browser lifecycle with async context manager support."""

    def __init__(self, config: BrowserConfig | None = None) -> None:
        self.config = config or BrowserConfig()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def _ensure_browser(self) -> Browser:
        """Lazily launch browser on first use."""
        if self._browser is None or not self._browser.is_connected():
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            launch_args: list[str] = []
            if self.config.headless:
                launch_args.append("--disable-gpu")
            self._browser = await self._playwright.chromium.launch(
                headless=self.config.headless,
                args=launch_args,
            )
            logger.debug("Browser launched (headless=%s)", self.config.headless)
        return self._browser

    async def new_context(self, **overrides: object) -> BrowserContext:
        """Create a new browser context with configured defaults."""
        browser = await self._ensure_browser()
        opts: dict[str, object] = {
            "viewport": {"width": self.config.viewport_width, "height": self.config.viewport_height},
            "locale": self.config.locale,
            "ignore_https_errors": self.config.ignore_https_errors,
        }
        if self.config.user_agent:
            opts["user_agent"] = self.config.user_agent
        opts.update(overrides)
        return await browser.new_context(**opts)  # type: ignore[arg-type]

    async def new_page(self, **context_overrides: object) -> Page:
        """Create a new page in a fresh context."""
        context = await self.new_context(**context_overrides)
        page = await context.new_page()
        page.set_default_timeout(self.config.timeout_ms)
        return page

    async def close(self) -> None:
        """Close browser and Playwright."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                logger.debug("Error closing browser", exc_info=True)
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                logger.debug("Error stopping Playwright", exc_info=True)
            self._playwright = None

    @property
    def is_running(self) -> bool:
        """Check if browser is active."""
        return self._browser is not None and self._browser.is_connected()

    async def __aenter__(self) -> BrowserManager:
        await self._ensure_browser()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()


# Module-level singleton for MCP server reuse
_default_manager: BrowserManager | None = None


async def get_manager(config: BrowserConfig | None = None) -> BrowserManager:
    """Get or create the default BrowserManager singleton."""
    global _default_manager
    if _default_manager is None or not _default_manager.is_running:
        _default_manager = BrowserManager(config)
    return _default_manager


async def close_manager() -> None:
    """Close the default BrowserManager singleton."""
    global _default_manager
    if _default_manager:
        await _default_manager.close()
        _default_manager = None
