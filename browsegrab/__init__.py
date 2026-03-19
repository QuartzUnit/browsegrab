"""browsegrab — Token-efficient browser agent for local LLMs.

Playwright + accessibility tree + MarkGrab, MCP native.
"""

from __future__ import annotations

__version__ = "0.1.1"

from browsegrab.config import BrowseGrabConfig
from browsegrab.result import ActionResult, BrowseResult, SnapshotResult
from browsegrab.session import BrowseSession

__all__ = [
    "BrowseGrabConfig",
    "BrowseSession",
    "ActionResult",
    "BrowseResult",
    "SnapshotResult",
]
