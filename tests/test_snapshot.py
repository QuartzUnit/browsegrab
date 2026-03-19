"""Tests for browsegrab.browser.snapshot module.

Uses the new Playwright locator.aria_snapshot() API.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from browsegrab.browser.snapshot import _augment_with_refs, _estimate_tokens, take_snapshot
from browsegrab.config import SnapshotConfig
from browsegrab.dom.ref_map import RefMap

# ── Sample aria_snapshot output ──────────────────────────────

SAMPLE_ARIA_SNAPSHOT = """\
- heading "Welcome" [level=1]
- link "About Us"
- textbox "Search"
- button "Submit"
- paragraph:
  - link "Home"
  - text: Some content here"""

SIMPLE_ARIA_SNAPSHOT = """\
- heading "Example Domain" [level=1]
- paragraph: This domain is for use in documentation.
- paragraph:
  - link "Learn more"
    - /url: https://example.com"""


def _make_mock_page(aria_text=SAMPLE_ARIA_SNAPSHOT, url="https://example.com", title="Test"):
    """Build a mock Playwright Page with locator('body').aria_snapshot()."""
    mock_page = MagicMock()
    mock_locator = MagicMock()
    mock_locator.aria_snapshot = AsyncMock(return_value=aria_text)
    mock_page.locator.return_value = mock_locator
    mock_page.url = url
    mock_page.title = AsyncMock(return_value=title)
    return mock_page


# ── _augment_with_refs unit tests ────────────────────────────


class TestAugmentWithRefs:
    def test_assigns_refs_to_interactive_elements(self):
        ref_map = RefMap()
        _augment_with_refs(SAMPLE_ARIA_SNAPSHOT, ref_map)
        # link "About Us", textbox "Search", button "Submit", link "Home" = 4
        assert ref_map.count == 4
        roles = {e.role for e in ref_map.all_elements()}
        assert "link" in roles
        assert "button" in roles
        assert "textbox" in roles

    def test_ref_ids_sequential(self):
        ref_map = RefMap()
        _augment_with_refs(SAMPLE_ARIA_SNAPSHOT, ref_map)
        elements = ref_map.all_elements()
        actual_refs = [e.ref for e in elements]
        expected = [f"e{i}" for i in range(1, len(elements) + 1)]
        assert actual_refs == expected

    def test_heading_not_assigned_ref(self):
        ref_map = RefMap()
        result = _augment_with_refs(SAMPLE_ARIA_SNAPSHOT, ref_map)
        assert "heading" in result
        assert "Welcome" in result
        for el in ref_map.all_elements():
            assert el.role != "heading"

    def test_ref_injected_into_text(self):
        ref_map = RefMap()
        result = _augment_with_refs(SAMPLE_ARIA_SNAPSHOT, ref_map)
        assert "[ref=e1]" in result
        assert "[ref=e2]" in result

    def test_existing_attrs_preserved(self):
        """Existing attributes like [level=1] should be preserved."""
        text = '- button "OK" [expanded]'
        ref_map = RefMap()
        result = _augment_with_refs(text, ref_map)
        assert "expanded" in result
        assert "ref=e1" in result

    def test_filter_interactive_only(self):
        ref_map = RefMap()
        result = _augment_with_refs(SAMPLE_ARIA_SNAPSHOT, ref_map, filter_interactive=True)
        # heading is a landmark, should be kept
        assert "heading" in result
        # interactive elements present
        assert "link" in result
        assert "button" in result


# ── take_snapshot integration tests ──────────────────────────


class TestRefAssignment:
    async def test_interactive_elements_get_refs(self):
        page = _make_mock_page()
        ref_map = RefMap()
        await take_snapshot(page, ref_map)
        assert ref_map.count == 4
        roles = {e.role for e in ref_map.all_elements()}
        assert "link" in roles
        assert "button" in roles
        assert "textbox" in roles

    async def test_ref_ids_sequential(self):
        page = _make_mock_page()
        ref_map = RefMap()
        await take_snapshot(page, ref_map)
        elements = ref_map.all_elements()
        expected_refs = [f"e{i}" for i in range(1, len(elements) + 1)]
        actual_refs = [e.ref for e in elements]
        assert actual_refs == expected_refs


class TestLandmarkInclusion:
    async def test_heading_included_in_text_but_not_in_ref_map(self):
        page = _make_mock_page()
        ref_map = RefMap()
        result = await take_snapshot(page, ref_map)
        assert "heading" in result.tree_text
        assert "Welcome" in result.tree_text
        for el in ref_map.all_elements():
            assert el.role != "heading"


class TestFilterInteractiveOnly:
    async def test_interactive_only_keeps_landmarks_and_interactive(self):
        page = _make_mock_page()
        ref_map = RefMap()
        config = SnapshotConfig(filter_interactive_only=True)
        result = await take_snapshot(page, ref_map, config)
        assert "link" in result.tree_text
        assert "button" in result.tree_text
        assert "textbox" in result.tree_text
        assert "heading" in result.tree_text

    async def test_interactive_only_excludes_non_interactive_lines(self):
        """Non-interactive, non-landmark lines are excluded."""
        text = "- StaticText \"Some text\"\n- button \"Click Me\""
        page = _make_mock_page(aria_text=text)
        ref_map = RefMap()
        config = SnapshotConfig(filter_interactive_only=True)
        result = await take_snapshot(page, ref_map, config)
        assert "button" in result.tree_text
        assert "StaticText" not in result.tree_text


class TestTruncation:
    async def test_truncation_when_exceeding_max_length(self):
        page = _make_mock_page()
        ref_map = RefMap()
        config = SnapshotConfig(max_snapshot_length=50)
        result = await take_snapshot(page, ref_map, config)
        assert len(result.tree_text) <= 50 + len("\n... (truncated)")
        assert result.tree_text.endswith("... (truncated)")


class TestEmptyAXTree:
    async def test_empty_aria_snapshot(self):
        page = _make_mock_page(aria_text="")
        ref_map = RefMap()
        result = await take_snapshot(page, ref_map)
        assert result.tree_text == "(empty page)"
        assert result.url == "https://example.com"

    async def test_null_aria_snapshot(self):
        page = _make_mock_page(aria_text=None)
        ref_map = RefMap()
        result = await take_snapshot(page, ref_map)
        assert result.tree_text == "(empty page)"

    async def test_snapshot_exception(self):
        page = _make_mock_page()
        mock_locator = AsyncMock()
        mock_locator.aria_snapshot = AsyncMock(side_effect=RuntimeError("browser crashed"))
        page.locator.return_value = mock_locator
        ref_map = RefMap()
        result = await take_snapshot(page, ref_map)
        assert result.tree_text == "(accessibility tree unavailable)"
        assert result.url == "https://example.com"


class TestTokenEstimation:
    def test_estimate_tokens_basic(self):
        assert _estimate_tokens("hello world") == max(1, len("hello world") // 4)

    def test_estimate_tokens_empty(self):
        assert _estimate_tokens("") == 1


class TestSnapshotMetadata:
    async def test_url_and_title_captured(self):
        page = _make_mock_page(url="https://test.com/page", title="My Page")
        ref_map = RefMap()
        result = await take_snapshot(page, ref_map)
        assert result.url == "https://test.com/page"
        assert result.title == "My Page"

    async def test_token_estimate_set(self):
        page = _make_mock_page()
        ref_map = RefMap()
        result = await take_snapshot(page, ref_map)
        assert result.token_estimate > 0
