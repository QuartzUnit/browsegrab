"""Accessibility tree extraction with ref system.

Uses Playwright's locator.aria_snapshot() API (1.49+) to get a compact
YAML-like accessibility tree, then augments interactive elements with
ref IDs for LLM-driven browser control.
"""

from __future__ import annotations

import logging
import re

from playwright.async_api import Page

from browsegrab.config import SnapshotConfig
from browsegrab.dom.ref_map import INTERACTIVE_ROLES, RefMap
from browsegrab.result import SnapshotResult

logger = logging.getLogger(__name__)

# Approximate tokens per character (conservative estimate for English/mixed)
CHARS_PER_TOKEN = 4

# Regex to match a role at the start of a line: "  - role "name" [attrs]"
_ROLE_RE = re.compile(r"^(\s*- )(\w+)(.*)")
# Regex to extract name from quotes: "name"
_NAME_RE = re.compile(r'"([^"]*)"')
# Regex to detect existing attributes in brackets: [level=1]
_ATTRS_RE = re.compile(r"\[([^\]]*)\]")


def _estimate_tokens(text: str) -> int:
    """Rough token count estimate."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def _augment_with_refs(tree_text: str, ref_map: RefMap, filter_interactive: bool = False) -> str:
    """Parse aria_snapshot text and inject ref IDs into interactive elements.

    Args:
        tree_text: Raw aria_snapshot output.
        ref_map: RefMap to populate (should be cleared before calling).
        filter_interactive: If True, omit lines that aren't interactive/landmark.

    Returns:
        Augmented tree text with [ref=eN] annotations.
    """
    lines = tree_text.split("\n")
    result_lines: list[str] = []

    for line in lines:
        match = _ROLE_RE.match(line)
        if not match:
            # Non-role lines (e.g. /url:, plain text content)
            if not filter_interactive:
                result_lines.append(line)
            continue

        indent = match.group(1)
        role = match.group(2)
        rest = match.group(3)

        # Extract name
        name_match = _NAME_RE.search(rest)
        name = name_match.group(1) if name_match else ""

        is_interactive = role in INTERACTIVE_ROLES

        if filter_interactive and not ref_map.should_include(role):
            continue

        if is_interactive:
            # Extract existing attributes
            attrs_match = _ATTRS_RE.search(rest)
            existing_attrs = attrs_match.group(1) if attrs_match else ""

            element = ref_map.assign(role=role, name=name)

            # Build new attributes
            new_attr = f"ref={element.ref}"
            combined_attrs = f"[{existing_attrs}, {new_attr}]" if existing_attrs else f"[{new_attr}]"

            # Replace or append attributes
            if attrs_match:
                new_rest = rest[: attrs_match.start()] + combined_attrs + rest[attrs_match.end() :]
            else:
                # Append after the role name/content
                new_rest = rest + f" {combined_attrs}"

            result_lines.append(f"{indent}{role}{new_rest}")
        else:
            result_lines.append(line)

    return "\n".join(result_lines)


async def take_snapshot(
    page: Page,
    ref_map: RefMap,
    config: SnapshotConfig | None = None,
) -> SnapshotResult:
    """Take an accessibility tree snapshot of the page.

    Uses Playwright's locator.aria_snapshot() for compact YAML-like output,
    then augments interactive elements with ref IDs.

    Args:
        page: Playwright page to snapshot.
        ref_map: RefMap instance (will be cleared and rebuilt).
        config: Snapshot configuration.

    Returns:
        SnapshotResult with formatted tree text and ref elements.
    """
    config = config or SnapshotConfig()
    ref_map.clear()

    # Get the accessibility tree via aria_snapshot
    try:
        raw_tree = await page.locator("body").aria_snapshot()
    except Exception as e:
        logger.warning("Failed to get aria snapshot: %s", e)
        return SnapshotResult(
            tree_text="(accessibility tree unavailable)",
            url=page.url,
            title=await page.title(),
        )

    if not raw_tree:
        return SnapshotResult(
            tree_text="(empty page)",
            url=page.url,
            title=await page.title(),
        )

    # Augment with ref IDs
    tree_text = _augment_with_refs(raw_tree, ref_map, config.filter_interactive_only)

    # Truncate if exceeding max length
    if len(tree_text) > config.max_snapshot_length:
        tree_text = tree_text[: config.max_snapshot_length] + "\n... (truncated)"

    title = await page.title()
    token_est = _estimate_tokens(tree_text)

    return SnapshotResult(
        tree_text=tree_text,
        elements=ref_map.all_elements(),
        ref_count=ref_map.count,
        url=page.url,
        title=title,
        token_estimate=token_est,
    )
