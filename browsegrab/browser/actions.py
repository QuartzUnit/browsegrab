"""Browser actions: navigate, click, type, scroll, go_back, wait."""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from browsegrab.browser.selectors import resolve_ref
from browsegrab.browser.snapshot import take_snapshot
from browsegrab.config import SnapshotConfig
from browsegrab.dom.ref_map import RefMap
from browsegrab.result import ActionResult

logger = logging.getLogger(__name__)


async def _post_action(
    page: Page,
    action: str,
    target: str,
    ref_map: RefMap,
    expectation: dict[str, Any] | None = None,
) -> ActionResult:
    """Build ActionResult after an action, optionally including snapshot/content."""
    exp = expectation or {}
    snapshot_text: str | None = None
    content_text: str | None = None
    token_est = 0

    if exp.get("include_snapshot", False):
        snap_config = SnapshotConfig(
            max_snapshot_length=exp.get("max_snapshot_length", 5000),
            filter_interactive_only=exp.get("filter_interactive_only", False),
        )
        snap = await take_snapshot(page, ref_map, snap_config)
        snapshot_text = snap.tree_text
        token_est += snap.token_estimate

    if exp.get("include_content", False):
        content_text = await _extract_content(page, exp.get("max_content_length", 3000))
        token_est += max(1, len(content_text) // 4) if content_text else 0

    return ActionResult(
        success=True,
        action=action,
        target=target,
        url=page.url,
        title=await page.title(),
        snapshot=snapshot_text,
        content=content_text,
        token_estimate=token_est,
    )


async def _extract_content(page: Page, max_length: int = 3000) -> str:
    """Extract page content as markdown via MarkGrab if available, else raw text."""
    try:
        from markgrab import parse as mg_parse

        html = await page.content()
        result = mg_parse(html, url=page.url)
        text = result.markdown if hasattr(result, "markdown") else str(result)
    except ImportError:
        # Fallback: get innerText
        text = await page.inner_text("body")
    except Exception as e:
        logger.debug("Content extraction error: %s", e)
        text = await page.inner_text("body")

    if len(text) > max_length:
        text = text[:max_length] + "\n... (truncated)"
    return text


async def navigate(
    page: Page,
    url: str,
    ref_map: RefMap,
    wait_until: str = "domcontentloaded",
    expectation: dict[str, Any] | None = None,
) -> ActionResult:
    """Navigate to a URL."""
    try:
        await page.goto(url, wait_until=wait_until)  # type: ignore[arg-type]
    except PlaywrightTimeout:
        return ActionResult(success=False, action="navigate", target=url, error="Navigation timeout")
    except Exception as e:
        return ActionResult(success=False, action="navigate", target=url, error=str(e))

    return await _post_action(page, "navigate", url, ref_map, expectation)


async def click(
    page: Page,
    ref: str,
    ref_map: RefMap,
    expectation: dict[str, Any] | None = None,
) -> ActionResult:
    """Click an element by ref ID."""
    locator = await resolve_ref(page, ref, ref_map)
    if locator is None:
        return ActionResult(success=False, action="click", target=ref, error=f"Cannot resolve ref: {ref}")

    try:
        await locator.click(timeout=10_000)
    except PlaywrightTimeout:
        return ActionResult(success=False, action="click", target=ref, error=f"Click timeout on {ref}")
    except Exception as e:
        return ActionResult(success=False, action="click", target=ref, error=str(e))

    # Wait briefly for navigation/rendering
    with contextlib.suppress(PlaywrightTimeout):
        await page.wait_for_load_state("domcontentloaded", timeout=5000)

    return await _post_action(page, "click", ref, ref_map, expectation)


async def type_text(
    page: Page,
    ref: str,
    text: str,
    ref_map: RefMap,
    clear: bool = True,
    submit: bool = False,
    expectation: dict[str, Any] | None = None,
) -> ActionResult:
    """Type text into an element by ref ID."""
    locator = await resolve_ref(page, ref, ref_map)
    if locator is None:
        return ActionResult(success=False, action="type", target=ref, error=f"Cannot resolve ref: {ref}")

    try:
        if clear:
            await locator.fill(text, timeout=10_000)
        else:
            await locator.press_sequentially(text, delay=50, timeout=10_000)

        if submit:
            await locator.press("Enter")
            with contextlib.suppress(PlaywrightTimeout):
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
    except PlaywrightTimeout:
        return ActionResult(success=False, action="type", target=ref, error=f"Type timeout on {ref}")
    except Exception as e:
        return ActionResult(success=False, action="type", target=ref, error=str(e))

    return await _post_action(page, "type", ref, ref_map, expectation)


async def scroll(
    page: Page,
    direction: str,
    ref_map: RefMap,
    amount: int = 500,
    ref: str | None = None,
    expectation: dict[str, Any] | None = None,
) -> ActionResult:
    """Scroll the page or a specific element."""
    target = ref or "page"
    delta_x = 0
    delta_y = amount if direction == "down" else -amount if direction == "up" else 0
    if direction == "right":
        delta_x = amount
    elif direction == "left":
        delta_x = -amount

    try:
        if ref:
            locator = await resolve_ref(page, ref, ref_map)
            if locator is None:
                return ActionResult(success=False, action="scroll", target=target, error=f"Cannot resolve ref: {ref}")
            await locator.scroll_into_view_if_needed()
            box = await locator.bounding_box()
            if box:
                await page.mouse.wheel(delta_x, delta_y)
        else:
            await page.mouse.wheel(delta_x, delta_y)
    except Exception as e:
        return ActionResult(success=False, action="scroll", target=target, error=str(e))

    # Brief wait for content to load after scroll
    await page.wait_for_timeout(300)

    return await _post_action(page, "scroll", f"{direction} {amount}px", ref_map, expectation)


async def go_back(
    page: Page,
    ref_map: RefMap,
    expectation: dict[str, Any] | None = None,
) -> ActionResult:
    """Navigate back in browser history."""
    try:
        await page.go_back(wait_until="domcontentloaded")
    except PlaywrightTimeout:
        return ActionResult(success=False, action="go_back", error="Go back timeout")
    except Exception as e:
        return ActionResult(success=False, action="go_back", error=str(e))

    return await _post_action(page, "go_back", "", ref_map, expectation)


async def wait(
    page: Page,
    ms: int = 1000,
    selector: str | None = None,
    state: str = "visible",
) -> ActionResult:
    """Wait for time or element state."""
    try:
        if selector:
            await page.locator(selector).wait_for(state=state, timeout=ms)  # type: ignore[arg-type]
        else:
            await page.wait_for_timeout(ms)
    except PlaywrightTimeout:
        return ActionResult(
            success=False,
            action="wait",
            target=selector or f"{ms}ms",
            error=f"Wait timeout: {selector or f'{ms}ms'}",
        )
    except Exception as e:
        return ActionResult(success=False, action="wait", target=selector or f"{ms}ms", error=str(e))

    return ActionResult(
        success=True,
        action="wait",
        target=selector or f"{ms}ms",
        url=page.url,
        title=await page.title(),
    )
