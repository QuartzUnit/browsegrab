"""Tests for browsegrab.session module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from browsegrab.config import BrowseGrabConfig
from browsegrab.session import BrowseSession


def _make_mock_manager():
    """Build a mock BrowserManager that produces mock pages."""
    manager = AsyncMock()
    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="Example")
    mock_page.is_closed = MagicMock(return_value=False)
    mock_page.goto = AsyncMock()
    mock_page.go_back = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.wait_for_load_state = AsyncMock()
    mock_page.mouse = MagicMock()
    mock_page.mouse.wheel = AsyncMock()
    mock_locator_body = MagicMock()
    mock_locator_body.aria_snapshot = AsyncMock(return_value='- heading "Hello" [level=1]\n- link "About"')
    mock_page.locator = MagicMock(return_value=mock_locator_body)
    mock_page.context = AsyncMock()
    mock_page.context.close = AsyncMock()

    manager.new_page = AsyncMock(return_value=mock_page)
    manager.close = AsyncMock()
    return manager, mock_page


# ── Context manager lifecycle ─────────────────────────────────


class TestBrowseSessionLifecycle:
    async def test_context_manager_enter_exit(self):
        """Session can be used as async context manager."""
        manager, _ = _make_mock_manager()
        config = BrowseGrabConfig()
        config.agent.enable_cache = False

        async with BrowseSession(config=config, manager=manager) as session:
            assert session is not None
            assert isinstance(session, BrowseSession)

    async def test_close_without_page(self):
        """Closing a session that never opened a page should not raise."""
        manager, _ = _make_mock_manager()
        config = BrowseGrabConfig()
        config.agent.enable_cache = False
        session = BrowseSession(config=config, manager=manager)

        # Should not raise
        await session.close()

    async def test_close_with_page(self):
        """Closing a session with an open page closes the page context."""
        manager, mock_page = _make_mock_manager()
        config = BrowseGrabConfig()
        config.agent.enable_cache = False

        session = BrowseSession(config=config, manager=manager)
        # Force page creation
        await session.navigate("https://example.com")

        await session.close()
        mock_page.context.close.assert_awaited_once()


# ── Manual navigate ───────────────────────────────────────────


class TestBrowseSessionNavigate:
    async def test_navigate(self):
        """session.navigate() calls page.goto."""
        manager, mock_page = _make_mock_manager()
        config = BrowseGrabConfig()
        config.agent.enable_cache = False

        async with BrowseSession(config=config, manager=manager) as session:
            result = await session.navigate("https://example.com")

            assert result.success is True
            mock_page.goto.assert_awaited_once()


# ── Manual snapshot ───────────────────────────────────────────


class TestBrowseSessionSnapshot:
    async def test_snapshot(self):
        """session.snapshot() returns SnapshotResult with tree text."""
        manager, mock_page = _make_mock_manager()
        config = BrowseGrabConfig()
        config.agent.enable_cache = False

        async with BrowseSession(config=config, manager=manager) as session:
            await session.navigate("https://example.com")
            snap = await session.snapshot()

            assert snap.tree_text != ""
            assert "heading" in snap.tree_text
            assert snap.url == "https://example.com"


# ── Manual click ──────────────────────────────────────────────


class TestBrowseSessionClick:
    @patch("browsegrab.browser.actions.resolve_ref")
    async def test_click(self, mock_resolve):
        """session.click() calls the click action."""
        manager, mock_page = _make_mock_manager()
        config = BrowseGrabConfig()
        config.agent.enable_cache = False

        mock_locator = AsyncMock()
        mock_resolve.return_value = mock_locator

        async with BrowseSession(config=config, manager=manager) as session:
            await session.navigate("https://example.com")
            result = await session.click("e1")

            assert result.success is True
            mock_locator.click.assert_awaited_once()


# ── Config defaults ───────────────────────────────────────────


class TestBrowseSessionConfig:
    def test_default_config_applied(self):
        """Session without explicit config uses BrowseGrabConfig defaults."""
        session = BrowseSession()

        assert session.config.browser.headless is True
        assert session.config.llm.provider == "vllm"
        assert session.config.snapshot.max_snapshot_length == 5000
        assert session.config.agent.max_steps == 10

    def test_custom_config_applied(self):
        """Session with custom config uses the provided values."""
        config = BrowseGrabConfig()
        config.agent.max_steps = 20
        config.browser.headless = False

        session = BrowseSession(config=config)

        assert session.config.agent.max_steps == 20
        assert session.config.browser.headless is False
