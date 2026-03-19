"""End-to-end integration tests using real Playwright browser.

These tests require Playwright Chromium to be installed:
    playwright install chromium

Skip with: pytest -m "not e2e"
"""

from __future__ import annotations

import pytest

from browsegrab import BrowseGrabConfig, BrowseSession

pytestmark = pytest.mark.e2e


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def config():
    """Config with cache disabled to avoid side effects."""
    cfg = BrowseGrabConfig()
    cfg.agent.enable_cache = False
    return cfg


# ── Navigate + Snapshot ──────────────────────────────────────


class TestNavigateSnapshot:
    async def test_navigate_example_com(self, config):
        async with BrowseSession(config=config) as session:
            result = await session.navigate("https://example.com")
            assert result.success
            assert "example.com" in result.url

    async def test_snapshot_example_com(self, config):
        async with BrowseSession(config=config) as session:
            await session.navigate("https://example.com")
            snap = await session.snapshot()

            assert snap.url == "https://example.com/"
            assert snap.title == "Example Domain"
            assert snap.ref_count >= 1
            assert snap.token_estimate > 0
            assert "heading" in snap.tree_text
            assert "Example Domain" in snap.tree_text

    async def test_ref_ids_assigned(self, config):
        async with BrowseSession(config=config) as session:
            await session.navigate("https://example.com")
            snap = await session.snapshot()

            # example.com has at least 1 link
            assert snap.ref_count >= 1
            assert "[ref=e1]" in snap.tree_text
            assert len(snap.elements) >= 1
            assert snap.elements[0].ref == "e1"

    async def test_snapshot_complex_page(self, config):
        """Wikipedia should produce many interactive elements."""
        async with BrowseSession(config=config) as session:
            await session.navigate("https://en.wikipedia.org/wiki/Main_Page")
            snap = await session.snapshot()

            # Wikipedia main page has 100+ interactive elements
            assert snap.ref_count > 50
            # Token estimate should be reasonable (not gigantic)
            assert snap.token_estimate < 5000


# ── Click ────────────────────────────────────────────────────


class TestClick:
    async def test_click_link(self, config):
        """Click the only link on example.com → navigates to IANA."""
        async with BrowseSession(config=config) as session:
            await session.navigate("https://example.com")
            snap = await session.snapshot()

            # Find the link ref
            link_elements = [e for e in snap.elements if e.role == "link"]
            assert len(link_elements) >= 1
            ref = link_elements[0].ref

            result = await session.click(ref)
            assert result.success
            assert "iana.org" in result.url

    async def test_click_invalid_ref(self, config):
        """Clicking a non-existent ref should fail gracefully."""
        async with BrowseSession(config=config) as session:
            await session.navigate("https://example.com")
            result = await session.click("e999")
            assert not result.success
            assert result.error is not None


# ── Type + Submit ────────────────────────────────────────────


class TestType:
    async def test_type_and_submit_search(self, config):
        """Type in Wikipedia search box and submit."""
        async with BrowseSession(config=config) as session:
            await session.navigate("https://en.wikipedia.org/wiki/Main_Page")
            snap = await session.snapshot()

            # Find searchbox
            search = [e for e in snap.elements if e.role == "searchbox"]
            assert len(search) >= 1
            ref = search[0].ref

            result = await session.type(ref, "Python programming", submit=True)
            assert result.success
            # Should navigate to Python article or search results
            assert "Python" in result.url or "search" in result.url.lower()


# ── Scroll ───────────────────────────────────────────────────


class TestScroll:
    async def test_scroll_down(self, config):
        async with BrowseSession(config=config) as session:
            await session.navigate("https://en.wikipedia.org/wiki/Web_browser")
            result = await session.scroll("down", 500)
            assert result.success

    async def test_scroll_up(self, config):
        async with BrowseSession(config=config) as session:
            await session.navigate("https://en.wikipedia.org/wiki/Web_browser")
            await session.scroll("down", 500)
            result = await session.scroll("up", 300)
            assert result.success


# ── Go Back ──────────────────────────────────────────────────


class TestGoBack:
    async def test_go_back(self, config):
        async with BrowseSession(config=config) as session:
            await session.navigate("https://example.com")
            snap = await session.snapshot()
            link_ref = snap.elements[0].ref

            # Navigate away
            await session.click(link_ref)
            snap2 = await session.snapshot()
            assert "iana.org" in snap2.url

            # Go back
            result = await session.go_back()
            assert result.success
            assert "example.com" in result.url


# ── Extract Content ──────────────────────────────────────────


class TestExtractContent:
    async def test_extract_content(self, config):
        async with BrowseSession(config=config) as session:
            await session.navigate("https://example.com")
            content = await session.extract_content()

            assert "[Page: Example Domain]" in content
            assert "[URL:" in content
            assert "[Elements:" in content
            assert "--- Content ---" in content
            assert "Example Domain" in content

    async def test_extract_content_scoped(self, config):
        """Extract content with CSS scope selector."""
        async with BrowseSession(config=config) as session:
            await session.navigate("https://en.wikipedia.org/wiki/Web_browser")
            content = await session.extract_content(scope="main")

            assert len(content) > 0
            assert "--- Content ---" in content


# ── Wait ─────────────────────────────────────────────────────


class TestWait:
    async def test_wait_ms(self, config):
        async with BrowseSession(config=config) as session:
            await session.navigate("https://example.com")
            result = await session.wait(ms=500)
            assert result.success


# ── Session Lifecycle ────────────────────────────────────────


class TestSessionLifecycle:
    async def test_multiple_navigations(self, config):
        """Session handles multiple navigations correctly."""
        async with BrowseSession(config=config) as session:
            await session.navigate("https://example.com")
            snap1 = await session.snapshot()
            assert "Example Domain" in snap1.title

            await session.navigate("https://en.wikipedia.org/wiki/Main_Page")
            snap2 = await session.snapshot()
            assert "Wikipedia" in snap2.title

            # Refs should reset between pages
            assert snap2.elements[0].ref == "e1"

    async def test_snapshot_after_click_updates_refs(self, config):
        """Refs are rebuilt after navigation via click."""
        async with BrowseSession(config=config) as session:
            await session.navigate("https://example.com")
            snap1 = await session.snapshot()
            old_count = snap1.ref_count

            await session.click("e1")
            snap2 = await session.snapshot()

            # New page should have different ref count
            assert snap2.ref_count != old_count or snap2.url != snap1.url


# ── Token Efficiency ─────────────────────────────────────────


class TestTokenEfficiency:
    async def test_token_budget_example_com(self, config):
        """example.com should be very cheap in tokens."""
        async with BrowseSession(config=config) as session:
            await session.navigate("https://example.com")
            snap = await session.snapshot()
            # Simple page should be under 200 tokens
            assert snap.token_estimate < 200

    async def test_token_budget_wikipedia(self, config):
        """Wikipedia article snapshot should stay within budget."""
        async with BrowseSession(config=config) as session:
            await session.navigate("https://en.wikipedia.org/wiki/Web_browser")
            snap = await session.snapshot()
            # Complex page should be under 2000 tokens (truncated at 5000 chars)
            assert snap.token_estimate < 2000
