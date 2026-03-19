"""Tests for browsegrab.browser.selectors module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from browsegrab.browser.selectors import (
    _try_role_selector,
    resolve_ref,
)
from browsegrab.dom.ref_map import RefMap
from browsegrab.result import RefElement


def _make_mock_page():
    """Build a mock Playwright Page with locator methods."""
    page = MagicMock()
    return page


def _make_ref_map_with(ref="e1", role="link", name="About Us"):
    """Create a RefMap with a single element pre-populated."""
    ref_map = RefMap()
    ref_map.assign(role=role, name=name)
    return ref_map


# ── resolve_ref: unknown ref ─────────────────────────────────


class TestResolveRefUnknown:
    async def test_unknown_ref_returns_none(self):
        page = _make_mock_page()
        ref_map = RefMap()  # empty

        result = await resolve_ref(page, "e99", ref_map)

        assert result is None


# ── Role selector: single match ──────────────────────────────


class TestRoleSelectorSingleMatch:
    async def test_role_selector_single_match(self):
        """When get_by_role returns exactly 1 match, use it."""
        page = _make_mock_page()
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=1)
        page.get_by_role = MagicMock(return_value=mock_locator)

        ref_map = _make_ref_map_with(role="button", name="Submit")
        result = await resolve_ref(page, "e1", ref_map)

        assert result is mock_locator
        page.get_by_role.assert_called_with("button", name="Submit", exact=False)


# ── Role selector: multiple matches → exact fallback ─────────


class TestRoleSelectorMultipleMatches:
    async def test_role_selector_multiple_then_exact(self):
        """When inexact returns >1, try exact=True."""
        page = _make_mock_page()

        # First call: inexact → 3 matches
        inexact_locator = MagicMock()
        inexact_locator.count = AsyncMock(return_value=3)

        # Second call: exact → 1 match
        exact_locator = MagicMock()
        exact_locator.count = AsyncMock(return_value=1)

        page.get_by_role = MagicMock(side_effect=[inexact_locator, exact_locator])

        ref_map = _make_ref_map_with(role="link", name="Home")
        result = await resolve_ref(page, "e1", ref_map)

        assert result is exact_locator
        # Should have been called twice: first inexact, then exact
        assert page.get_by_role.call_count == 2


# ── Text selector as fallback ────────────────────────────────


class TestTextSelectorFallback:
    async def test_text_selector_when_role_fails(self):
        """When role selector returns 0 matches, fall through to text selector."""
        page = _make_mock_page()

        # Role returns 0
        role_locator = MagicMock()
        role_locator.count = AsyncMock(return_value=0)
        page.get_by_role = MagicMock(return_value=role_locator)

        # CSS selector path: element has no selector, so _try_css_selector returns None
        css_locator = MagicMock()
        css_locator.count = AsyncMock(return_value=0)
        page.locator = MagicMock(return_value=css_locator)

        # Text selector returns 1
        text_locator = MagicMock()
        text_locator.count = AsyncMock(return_value=1)
        page.get_by_text = MagicMock(return_value=text_locator)

        ref_map = _make_ref_map_with(role="link", name="About Us")
        result = await resolve_ref(page, "e1", ref_map)

        assert result is text_locator


# ── _try_role_selector with empty role or name ────────────────


class TestRoleSelectorEdgeCases:
    async def test_role_selector_empty_name_returns_none(self):
        """If element has no name, _try_role_selector returns None."""
        page = _make_mock_page()
        element = RefElement(ref="e1", role="button", name="")

        result = await _try_role_selector(page, element)

        assert result is None

    async def test_role_selector_empty_role_returns_none(self):
        """If element has no role, _try_role_selector returns None."""
        page = _make_mock_page()
        element = RefElement(ref="e1", role="", name="Click")

        result = await _try_role_selector(page, element)

        assert result is None
