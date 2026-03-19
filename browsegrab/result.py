"""Result dataclasses for browsegrab operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RefElement:
    """A single element in the ref system."""

    ref: str  # e.g. "e1", "e2"
    role: str  # e.g. "link", "button", "textbox"
    name: str  # accessible name
    tag: str = ""  # HTML tag name
    value: str = ""  # current value (for inputs)
    level: int = 0  # heading level
    focused: bool = False
    checked: bool | None = None  # for checkboxes
    expanded: bool | None = None  # for accordions
    selector: str = ""  # resolved CSS selector


@dataclass
class SnapshotResult:
    """Result of an accessibility tree snapshot."""

    tree_text: str  # formatted AX tree string
    elements: list[RefElement] = field(default_factory=list)
    ref_count: int = 0
    url: str = ""
    title: str = ""
    token_estimate: int = 0

    def get_element(self, ref: str) -> RefElement | None:
        """Look up element by ref ID."""
        for el in self.elements:
            if el.ref == ref:
                return el
        return None


@dataclass
class ActionResult:
    """Result of a single browser action."""

    success: bool
    action: str  # e.g. "click", "navigate", "type"
    target: str = ""  # ref ID or URL
    url: str = ""  # current page URL after action
    title: str = ""  # current page title after action
    snapshot: str | None = None  # AX tree if requested
    content: str | None = None  # MarkGrab markdown if requested
    error: str | None = None
    token_estimate: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict, omitting None values."""
        d: dict[str, Any] = {
            "success": self.success,
            "action": self.action,
        }
        if self.target:
            d["target"] = self.target
        if self.url:
            d["url"] = self.url
        if self.title:
            d["title"] = self.title
        if self.snapshot is not None:
            d["snapshot"] = self.snapshot
        if self.content is not None:
            d["content"] = self.content
        if self.error is not None:
            d["error"] = self.error
        if self.token_estimate:
            d["token_estimate"] = self.token_estimate
        return d


@dataclass
class StepRecord:
    """Record of a single agent step for history tracking."""

    step: int
    action: str
    target: str = ""
    url: str = ""
    summary: str = ""
    success: bool = True


@dataclass
class BrowseResult:
    """Final result of an agentic browse session."""

    success: bool
    url: str = ""
    title: str = ""
    content: str = ""  # extracted markdown content
    snapshot: str = ""  # final AX tree snapshot
    steps: list[StepRecord] = field(default_factory=list)
    total_steps: int = 0
    total_tokens: int = 0
    processing_time_ms: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        d: dict[str, Any] = {
            "success": self.success,
            "url": self.url,
            "title": self.title,
            "total_steps": self.total_steps,
            "total_tokens": self.total_tokens,
            "processing_time_ms": self.processing_time_ms,
        }
        if self.content:
            d["content"] = self.content
        if self.snapshot:
            d["snapshot"] = self.snapshot
        if self.steps:
            d["steps"] = [
                {"step": s.step, "action": s.action, "target": s.target, "success": s.success} for s in self.steps
            ]
        if self.error:
            d["error"] = self.error
        if self.metadata:
            d["metadata"] = self.metadata
        return d
