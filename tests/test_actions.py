"""Tests for browsegrab.browser.actions module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from playwright.async_api import TimeoutError as PlaywrightTimeout

from browsegrab.browser.actions import click, go_back, navigate, scroll, type_text, wait
from browsegrab.dom.ref_map import RefMap


def _make_mock_page(url="https://example.com", title="Test"):
    """Build a mock Playwright Page."""
    page = AsyncMock()
    page.url = url
    page.title = AsyncMock(return_value=title)
    page.goto = AsyncMock()
    page.go_back = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.mouse = MagicMock()
    page.mouse.wheel = AsyncMock()
    return page


def _make_ref_map_with_element(ref="e1", role="link", name="About Us"):
    """Create a RefMap pre-populated with one element."""
    ref_map = RefMap()
    ref_map.assign(role=role, name=name)
    return ref_map


# ── navigate() ────────────────────────────────────────────────


class TestNavigate:
    async def test_navigate_success(self):
        page = _make_mock_page()
        ref_map = RefMap()
        result = await navigate(page, "https://example.com", ref_map)

        assert result.success is True
        assert result.action == "navigate"
        page.goto.assert_awaited_once_with("https://example.com", wait_until="domcontentloaded")

    async def test_navigate_timeout(self):
        page = _make_mock_page()
        page.goto = AsyncMock(side_effect=PlaywrightTimeout("Navigation timeout"))
        ref_map = RefMap()
        result = await navigate(page, "https://slow.example.com", ref_map)

        assert result.success is False
        assert result.action == "navigate"
        assert "timeout" in result.error.lower()

    async def test_navigate_generic_error(self):
        page = _make_mock_page()
        page.goto = AsyncMock(side_effect=RuntimeError("net::ERR_NAME_NOT_RESOLVED"))
        ref_map = RefMap()
        result = await navigate(page, "https://bad.invalid", ref_map)

        assert result.success is False
        assert "ERR_NAME_NOT_RESOLVED" in result.error


# ── click() ───────────────────────────────────────────────────


class TestClick:
    @patch("browsegrab.browser.actions.resolve_ref")
    async def test_click_success(self, mock_resolve):
        page = _make_mock_page()
        ref_map = _make_ref_map_with_element()

        mock_locator = AsyncMock()
        mock_resolve.return_value = mock_locator

        result = await click(page, "e1", ref_map)

        assert result.success is True
        assert result.action == "click"
        mock_locator.click.assert_awaited_once_with(timeout=10_000)

    @patch("browsegrab.browser.actions.resolve_ref")
    async def test_click_ref_not_found(self, mock_resolve):
        page = _make_mock_page()
        ref_map = RefMap()
        mock_resolve.return_value = None

        result = await click(page, "e999", ref_map)

        assert result.success is False
        assert "Cannot resolve ref" in result.error

    @patch("browsegrab.browser.actions.resolve_ref")
    async def test_click_timeout(self, mock_resolve):
        page = _make_mock_page()
        ref_map = _make_ref_map_with_element()

        mock_locator = AsyncMock()
        mock_locator.click = AsyncMock(side_effect=PlaywrightTimeout("Click timeout"))
        mock_resolve.return_value = mock_locator

        result = await click(page, "e1", ref_map)

        assert result.success is False
        assert "timeout" in result.error.lower()


# ── type_text() ───────────────────────────────────────────────


class TestTypeText:
    @patch("browsegrab.browser.actions.resolve_ref")
    async def test_type_with_clear(self, mock_resolve):
        """clear=True should call locator.fill()."""
        page = _make_mock_page()
        ref_map = _make_ref_map_with_element(role="textbox", name="Search")

        mock_locator = AsyncMock()
        mock_resolve.return_value = mock_locator

        result = await type_text(page, "e1", "hello", ref_map, clear=True, submit=False)

        assert result.success is True
        mock_locator.fill.assert_awaited_once_with("hello", timeout=10_000)
        mock_locator.press.assert_not_awaited()

    @patch("browsegrab.browser.actions.resolve_ref")
    async def test_type_with_submit(self, mock_resolve):
        """submit=True should call locator.press('Enter')."""
        page = _make_mock_page()
        ref_map = _make_ref_map_with_element(role="textbox", name="Search")

        mock_locator = AsyncMock()
        mock_resolve.return_value = mock_locator

        result = await type_text(page, "e1", "query", ref_map, clear=True, submit=True)

        assert result.success is True
        mock_locator.fill.assert_awaited_once()
        mock_locator.press.assert_awaited_once_with("Enter")


# ── scroll() ──────────────────────────────────────────────────


class TestScroll:
    async def test_scroll_down(self):
        page = _make_mock_page()
        ref_map = RefMap()

        result = await scroll(page, "down", ref_map, amount=500)

        assert result.success is True
        assert result.action == "scroll"
        page.mouse.wheel.assert_awaited_once_with(0, 500)

    async def test_scroll_up(self):
        page = _make_mock_page()
        ref_map = RefMap()

        result = await scroll(page, "up", ref_map, amount=300)

        assert result.success is True
        page.mouse.wheel.assert_awaited_once_with(0, -300)


# ── go_back() ─────────────────────────────────────────────────


class TestGoBack:
    async def test_go_back_success(self):
        page = _make_mock_page()
        ref_map = RefMap()

        result = await go_back(page, ref_map)

        assert result.success is True
        assert result.action == "go_back"
        page.go_back.assert_awaited_once_with(wait_until="domcontentloaded")


# ── wait() ────────────────────────────────────────────────────


class TestWait:
    async def test_wait_timeout_ms(self):
        page = _make_mock_page()

        result = await wait(page, ms=2000)

        assert result.success is True
        assert result.action == "wait"
        page.wait_for_timeout.assert_awaited_once_with(2000)

    async def test_wait_with_selector(self):
        page = _make_mock_page()
        mock_locator = MagicMock()
        mock_locator.wait_for = AsyncMock()
        page.locator = MagicMock(return_value=mock_locator)

        result = await wait(page, ms=5000, selector="#loading")

        assert result.success is True
        page.locator.assert_called_once_with("#loading")
        mock_locator.wait_for.assert_awaited_once_with(state="visible", timeout=5000)
