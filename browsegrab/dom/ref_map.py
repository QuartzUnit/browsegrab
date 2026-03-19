"""Ref ID ↔ element bidirectional mapping.

The ref system assigns short IDs (e1, e2, ...) to interactive elements
in the accessibility tree, enabling LLMs to reference elements cheaply.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from browsegrab.result import RefElement

# Roles considered interactive (actionable by the user/agent)
INTERACTIVE_ROLES = frozenset({
    "link",
    "button",
    "textbox",
    "checkbox",
    "radio",
    "combobox",
    "listbox",
    "option",
    "menuitem",
    "tab",
    "switch",
    "slider",
    "spinbutton",
    "searchbox",
    "menuitemcheckbox",
    "menuitemradio",
    "treeitem",
})

# Roles for structural landmarks (included for navigation context)
LANDMARK_ROLES = frozenset({
    "heading",
    "navigation",
    "main",
    "banner",
    "contentinfo",
    "complementary",
    "form",
    "region",
    "dialog",
    "alertdialog",
    "alert",
})


@dataclass
class RefMap:
    """Bidirectional mapping between ref IDs and accessibility tree elements."""

    _elements: dict[str, RefElement] = field(default_factory=dict)
    _counter: int = 0

    def clear(self) -> None:
        """Reset the ref map for a new snapshot."""
        self._elements.clear()
        self._counter = 0

    def assign(self, role: str, name: str, **attrs: Any) -> RefElement:
        """Assign a new ref ID to an element and return the RefElement."""
        self._counter += 1
        ref = f"e{self._counter}"
        element = RefElement(
            ref=ref,
            role=role,
            name=name,
            tag=attrs.get("tag", ""),
            value=attrs.get("value", ""),
            level=attrs.get("level", 0),
            focused=attrs.get("focused", False),
            checked=attrs.get("checked"),
            expanded=attrs.get("expanded"),
            selector=attrs.get("selector", ""),
        )
        self._elements[ref] = element
        return element

    def get(self, ref: str) -> RefElement | None:
        """Look up element by ref ID."""
        return self._elements.get(ref)

    def all_elements(self) -> list[RefElement]:
        """Return all mapped elements in assignment order."""
        return list(self._elements.values())

    @property
    def count(self) -> int:
        """Number of elements in the map."""
        return len(self._elements)

    def is_interactive(self, role: str) -> bool:
        """Check if a role is interactive."""
        return role in INTERACTIVE_ROLES

    def is_landmark(self, role: str) -> bool:
        """Check if a role is a structural landmark."""
        return role in LANDMARK_ROLES

    def should_include(self, role: str) -> bool:
        """Check if a role should be included in the snapshot."""
        return role in INTERACTIVE_ROLES or role in LANDMARK_ROLES
