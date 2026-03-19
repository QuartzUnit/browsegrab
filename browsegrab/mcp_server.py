"""MCP server for browsegrab — 8 browser automation tools.

Start: browsegrab-mcp (stdio transport)
"""

from __future__ import annotations

import json
import logging
from typing import Any

try:
    from fastmcp import FastMCP
except ImportError as exc:
    raise ImportError("MCP server requires: pip install browsegrab[mcp]") from exc

from browsegrab.config import BrowseGrabConfig  # noqa: E402
from browsegrab.session import BrowseSession  # noqa: E402

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "browsegrab",
    instructions=(
        "Token-efficient browser agent for local LLMs. "
        "Uses accessibility tree + MarkGrab for ~500-1,500 tokens/step. "
        "Elements are referenced by short IDs: e1, e2, etc."
    ),
)

# Shared state across tool calls in a single MCP session
_session: BrowseSession | None = None
_config: BrowseGrabConfig | None = None


async def _get_session() -> BrowseSession:
    """Get or create the shared BrowseSession."""
    global _session, _config
    if _session is None:
        _config = BrowseGrabConfig.from_env()
        _session = BrowseSession(_config)
    return _session


def _json_response(data: dict[str, Any]) -> str:
    """Serialize response dict to JSON string."""
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
async def browser_navigate(url: str, wait_until: str = "domcontentloaded") -> str:
    """Navigate to a URL and return accessibility tree snapshot.

    Args:
        url: The URL to navigate to.
        wait_until: When to consider navigation done (domcontentloaded, load, networkidle).
    """
    session = await _get_session()
    result = await session.navigate(url, include_snapshot=True)
    snap = await session.snapshot()
    return _json_response({
        "success": result.success,
        "url": result.url,
        "title": result.title,
        "snapshot": snap.tree_text,
        "ref_count": snap.ref_count,
        "token_estimate": snap.token_estimate,
        "error": result.error,
    })


@mcp.tool()
async def browser_click(ref: str) -> str:
    """Click an element by its ref ID (e.g. 'e1', 'e5').

    Args:
        ref: Element ref ID from the accessibility tree snapshot.
    """
    session = await _get_session()
    result = await session.click(ref, include_snapshot=True)
    return _json_response(result.to_dict())


@mcp.tool()
async def browser_type(ref: str, text: str, clear: bool = True, submit: bool = False) -> str:
    """Type text into an input element.

    Args:
        ref: Element ref ID (e.g. 'e3' for a textbox).
        text: The text to type.
        clear: Clear existing content before typing (default: true).
        submit: Press Enter after typing (default: false).
    """
    session = await _get_session()
    result = await session.type(ref, text, clear=clear, submit=submit, include_snapshot=True)
    return _json_response(result.to_dict())


@mcp.tool()
async def browser_snapshot(interactive_only: bool = False, max_length: int = 5000) -> str:
    """Get the current page accessibility tree snapshot.

    Args:
        interactive_only: Only show interactive elements (buttons, links, inputs).
        max_length: Maximum snapshot text length.
    """
    session = await _get_session()
    snap = await session.snapshot()
    return _json_response({
        "url": snap.url,
        "title": snap.title,
        "ref_count": snap.ref_count,
        "token_estimate": snap.token_estimate,
        "snapshot": snap.tree_text[:max_length],
    })


@mcp.tool()
async def browser_scroll(direction: str = "down", amount: int = 500, ref: str | None = None) -> str:
    """Scroll the page or a specific element.

    Args:
        direction: Scroll direction (up, down, left, right).
        amount: Scroll amount in pixels.
        ref: Optional element ref ID to scroll into view first.
    """
    session = await _get_session()
    result = await session.scroll(direction=direction, amount=amount, ref=ref, include_snapshot=True)
    return _json_response(result.to_dict())


@mcp.tool()
async def browser_extract_content(scope: str | None = None, max_length: int = 3000) -> str:
    """Extract page content as clean markdown (via MarkGrab if available).

    Args:
        scope: CSS selector to limit extraction scope (e.g. 'main', '.article').
        max_length: Maximum content length.
    """
    session = await _get_session()
    content = await session.extract_content(max_length=max_length, scope=scope)
    return _json_response({"content": content})


@mcp.tool()
async def browser_go_back() -> str:
    """Navigate back in browser history."""
    session = await _get_session()
    result = await session.go_back(include_snapshot=True)
    return _json_response(result.to_dict())


@mcp.tool()
async def browser_wait(ms: int = 1000, selector: str | None = None, state: str = "visible") -> str:
    """Wait for a specified time or until an element reaches a state.

    Args:
        ms: Milliseconds to wait (or timeout for selector wait).
        selector: CSS selector to wait for.
        state: Target element state (visible, hidden, attached, detached).
    """
    session = await _get_session()
    result = await session.wait(ms=ms, selector=selector, state=state)
    return _json_response(result.to_dict())


def main():
    """Entry point for browsegrab-mcp command."""
    mcp.run()


if __name__ == "__main__":
    main()
