"""4-strategy selector resolver.

Resolves a ref ID or description to a Playwright locator,
trying strategies in order: ref → role → css → text.
"""

from __future__ import annotations

import logging

from playwright.async_api import Locator, Page

from browsegrab.dom.ref_map import RefMap
from browsegrab.result import RefElement

logger = logging.getLogger(__name__)


async def _try_role_selector(page: Page, element: RefElement) -> Locator | None:
    """Try ARIA role-based selector."""
    role = element.role
    name = element.name
    if not role or not name:
        return None

    try:
        locator = page.get_by_role(role, name=name, exact=False)  # type: ignore[arg-type]
        count = await locator.count()
        if count == 1:
            return locator
        if count > 1:
            # Try exact match
            locator = page.get_by_role(role, name=name, exact=True)  # type: ignore[arg-type]
            if await locator.count() == 1:
                return locator
    except Exception:
        logger.debug("Role selector failed for %s", element.ref)
    return None


async def _try_css_selector(page: Page, element: RefElement) -> Locator | None:
    """Try CSS selector if available."""
    if not element.selector:
        return None
    try:
        locator = page.locator(element.selector)
        if await locator.count() == 1:
            return locator
    except Exception:
        logger.debug("CSS selector failed for %s: %s", element.ref, element.selector)
    return None


async def _try_text_selector(page: Page, element: RefElement) -> Locator | None:
    """Try text-based selector as last resort."""
    if not element.name:
        return None
    try:
        locator = page.get_by_text(element.name, exact=True)
        if await locator.count() == 1:
            return locator
        # Fallback to partial match
        locator = page.get_by_text(element.name, exact=False)
        if await locator.count() == 1:
            return locator
    except Exception:
        logger.debug("Text selector failed for %s", element.ref)
    return None


async def resolve_ref(page: Page, ref: str, ref_map: RefMap) -> Locator | None:
    """Resolve a ref ID to a Playwright Locator using 4-strategy fallback.

    Strategy order (fastest first):
    1. Role selector (ARIA role + name) — ~5ms
    2. CSS selector (if stored)         — ~1ms
    3. Text selector (accessible name)  — ~10ms
    4. None (all strategies failed)

    Args:
        page: Current Playwright page.
        ref: Ref ID (e.g. "e1", "e5").
        ref_map: Current RefMap with element info.

    Returns:
        Playwright Locator or None if unresolvable.
    """
    element = ref_map.get(ref)
    if element is None:
        logger.warning("Unknown ref: %s", ref)
        return None

    # Strategy 1: ARIA role
    locator = await _try_role_selector(page, element)
    if locator:
        logger.debug("Resolved %s via role selector", ref)
        return locator

    # Strategy 2: CSS selector
    locator = await _try_css_selector(page, element)
    if locator:
        logger.debug("Resolved %s via CSS selector", ref)
        return locator

    # Strategy 3: Text content
    locator = await _try_text_selector(page, element)
    if locator:
        logger.debug("Resolved %s via text selector", ref)
        return locator

    logger.warning("Could not resolve ref %s (role=%s, name=%s)", ref, element.role, element.name)
    return None
