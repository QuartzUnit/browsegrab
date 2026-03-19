"""DOM compression: AX tree (structure) + MarkGrab (content).

This is the core differentiator — combining accessibility tree for
structure with MarkGrab for clean content extraction, achieving
~500-1,300 tokens per step vs 4K-10K for alternatives.
"""

from __future__ import annotations

import logging

from playwright.async_api import Page

from browsegrab.browser.snapshot import take_snapshot
from browsegrab.config import SnapshotConfig
from browsegrab.dom.ref_map import RefMap

logger = logging.getLogger(__name__)


async def compress_dom(
    page: Page,
    ref_map: RefMap,
    config: SnapshotConfig | None = None,
    include_content: bool = False,
    scope_selector: str | None = None,
) -> str:
    """Produce a compressed DOM representation for LLM consumption.

    Combines:
    - Path A: Accessibility tree (structure, interactive elements)
    - Path B: MarkGrab markdown (content, on-demand)

    Args:
        page: Playwright page.
        ref_map: RefMap to populate.
        config: Snapshot configuration.
        include_content: Whether to include MarkGrab content.
        scope_selector: CSS selector to limit scope (e.g. ".main").

    Returns:
        Compressed text representation.
    """
    config = config or SnapshotConfig()
    parts: list[str] = []

    # Path A: Accessibility tree
    snapshot = await take_snapshot(page, ref_map, config)
    if snapshot.tree_text:
        parts.append(f"[Page: {snapshot.title}]")
        parts.append(f"[URL: {snapshot.url}]")
        parts.append(f"[Elements: {snapshot.ref_count} interactive]")
        parts.append("")
        parts.append(snapshot.tree_text)

    # Path B: MarkGrab content (optional, on-demand)
    if include_content:
        content = await _extract_markdown(page, config.max_content_length, scope_selector)
        if content:
            parts.append("")
            parts.append("--- Content ---")
            parts.append(content)

    result = "\n".join(parts)

    # Final truncation safety
    max_total = config.max_snapshot_length + (config.max_content_length if include_content else 0)
    if len(result) > max_total:
        result = result[:max_total] + "\n... (truncated)"

    return result


async def _extract_markdown(
    page: Page,
    max_length: int = 3000,
    scope_selector: str | None = None,
) -> str:
    """Extract clean markdown content from the page.

    Uses MarkGrab if available, falls back to innerText.
    """
    try:
        html = await _get_scoped_html(page, scope_selector)
        return _markgrab_convert(html, page.url, max_length)
    except ImportError:
        return await _fallback_text(page, max_length, scope_selector)
    except Exception as e:
        logger.debug("MarkGrab extraction failed, using fallback: %s", e)
        return await _fallback_text(page, max_length, scope_selector)


async def _get_scoped_html(page: Page, scope_selector: str | None) -> str:
    """Get HTML, optionally scoped to a CSS selector."""
    if scope_selector:
        try:
            element = page.locator(scope_selector)
            if await element.count() > 0:
                return await element.first.inner_html()
        except Exception:
            logger.debug("Scope selector %s failed, using full page", scope_selector)
    return await page.content()


def _markgrab_convert(html: str, url: str, max_length: int) -> str:
    """Convert HTML to markdown using MarkGrab."""
    from markgrab import parse as mg_parse

    result = mg_parse(html, url=url)
    text = result.markdown if hasattr(result, "markdown") else str(result)

    if len(text) > max_length:
        text = text[:max_length] + "\n... (truncated)"
    return text


async def _fallback_text(page: Page, max_length: int, scope_selector: str | None = None) -> str:
    """Fallback: extract plain text."""
    try:
        if scope_selector:
            element = page.locator(scope_selector)
            if await element.count() > 0:
                text = await element.first.inner_text()
            else:
                text = await page.inner_text("body")
        else:
            text = await page.inner_text("body")
    except Exception:
        text = ""

    if len(text) > max_length:
        text = text[:max_length] + "\n... (truncated)"
    return text
