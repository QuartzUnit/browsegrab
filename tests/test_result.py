"""Tests for browsegrab.result module."""

from __future__ import annotations

from browsegrab.result import (
    ActionResult,
    BrowseResult,
    RefElement,
    SnapshotResult,
    StepRecord,
)

# ── RefElement ─────────────────────────────────────────────────


class TestRefElement:
    def test_required_fields(self):
        el = RefElement(ref="e1", role="button", name="Submit")
        assert el.ref == "e1"
        assert el.role == "button"
        assert el.name == "Submit"

    def test_optional_defaults(self):
        el = RefElement(ref="e2", role="link", name="Home")
        assert el.tag == ""
        assert el.value == ""
        assert el.level == 0
        assert el.focused is False
        assert el.checked is None
        assert el.expanded is None
        assert el.selector == ""

    def test_all_fields(self):
        el = RefElement(
            ref="e3",
            role="textbox",
            name="Search",
            tag="input",
            value="hello",
            level=0,
            focused=True,
            checked=None,
            expanded=None,
            selector="input#search",
        )
        assert el.tag == "input"
        assert el.value == "hello"
        assert el.focused is True
        assert el.selector == "input#search"


# ── SnapshotResult ─────────────────────────────────────────────


class TestSnapshotResult:
    def test_minimal(self):
        snap = SnapshotResult(tree_text="[doc] Page Title")
        assert snap.tree_text == "[doc] Page Title"
        assert snap.elements == []
        assert snap.ref_count == 0
        assert snap.url == ""
        assert snap.title == ""
        assert snap.token_estimate == 0

    def test_get_element_found(self):
        el1 = RefElement(ref="e1", role="button", name="OK")
        el2 = RefElement(ref="e2", role="link", name="Cancel")
        snap = SnapshotResult(tree_text="tree", elements=[el1, el2], ref_count=2)
        result = snap.get_element("e2")
        assert result is el2

    def test_get_element_not_found(self):
        el1 = RefElement(ref="e1", role="button", name="OK")
        snap = SnapshotResult(tree_text="tree", elements=[el1], ref_count=1)
        assert snap.get_element("e99") is None

    def test_get_element_empty_list(self):
        snap = SnapshotResult(tree_text="empty")
        assert snap.get_element("e1") is None


# ── ActionResult ───────────────────────────────────────────────


class TestActionResult:
    def test_to_dict_minimal(self):
        ar = ActionResult(success=True, action="navigate")
        d = ar.to_dict()
        assert d == {"success": True, "action": "navigate"}
        # None/empty fields should be omitted
        assert "target" not in d
        assert "url" not in d
        assert "title" not in d
        assert "snapshot" not in d
        assert "content" not in d
        assert "error" not in d
        assert "token_estimate" not in d

    def test_to_dict_all_fields(self):
        ar = ActionResult(
            success=True,
            action="click",
            target="e5",
            url="https://example.com",
            title="Example",
            snapshot="[doc] ...",
            content="# Heading",
            error=None,
            token_estimate=150,
        )
        d = ar.to_dict()
        assert d["success"] is True
        assert d["action"] == "click"
        assert d["target"] == "e5"
        assert d["url"] == "https://example.com"
        assert d["title"] == "Example"
        assert d["snapshot"] == "[doc] ..."
        assert d["content"] == "# Heading"
        assert d["token_estimate"] == 150
        assert "error" not in d  # None is omitted

    def test_to_dict_error(self):
        ar = ActionResult(success=False, action="click", error="Element not found")
        d = ar.to_dict()
        assert d["success"] is False
        assert d["error"] == "Element not found"

    def test_to_dict_zero_token_estimate_omitted(self):
        ar = ActionResult(success=True, action="navigate", token_estimate=0)
        d = ar.to_dict()
        assert "token_estimate" not in d


# ── StepRecord ─────────────────────────────────────────────────


class TestStepRecord:
    def test_creation(self):
        sr = StepRecord(step=1, action="navigate")
        assert sr.step == 1
        assert sr.action == "navigate"
        assert sr.target == ""
        assert sr.url == ""
        assert sr.summary == ""
        assert sr.success is True

    def test_full_fields(self):
        sr = StepRecord(
            step=3,
            action="click",
            target="e7",
            url="https://example.com/page",
            summary="Clicked button",
            success=False,
        )
        assert sr.step == 3
        assert sr.target == "e7"
        assert sr.url == "https://example.com/page"
        assert sr.summary == "Clicked button"
        assert sr.success is False


# ── BrowseResult ───────────────────────────────────────────────


class TestBrowseResult:
    def test_to_dict_minimal(self):
        br = BrowseResult(success=True)
        d = br.to_dict()
        assert d == {
            "success": True,
            "url": "",
            "title": "",
            "total_steps": 0,
            "total_tokens": 0,
            "processing_time_ms": 0.0,
        }
        # Empty/None optional fields omitted
        assert "content" not in d
        assert "snapshot" not in d
        assert "steps" not in d
        assert "error" not in d
        assert "metadata" not in d

    def test_to_dict_with_content_and_steps(self):
        steps = [
            StepRecord(step=1, action="navigate", target="https://example.com", success=True),
            StepRecord(step=2, action="click", target="e3", success=True),
        ]
        br = BrowseResult(
            success=True,
            url="https://example.com",
            title="Example",
            content="# Hello",
            snapshot="[doc] tree",
            steps=steps,
            total_steps=2,
            total_tokens=300,
            processing_time_ms=1500.5,
            metadata={"session_id": "abc123"},
        )
        d = br.to_dict()
        assert d["success"] is True
        assert d["url"] == "https://example.com"
        assert d["title"] == "Example"
        assert d["content"] == "# Hello"
        assert d["snapshot"] == "[doc] tree"
        assert d["total_steps"] == 2
        assert d["total_tokens"] == 300
        assert d["processing_time_ms"] == 1500.5
        assert d["metadata"] == {"session_id": "abc123"}
        # Steps serialized
        assert len(d["steps"]) == 2
        assert d["steps"][0] == {"step": 1, "action": "navigate", "target": "https://example.com", "success": True}
        assert d["steps"][1] == {"step": 2, "action": "click", "target": "e3", "success": True}

    def test_to_dict_with_error(self):
        br = BrowseResult(success=False, error="Timeout exceeded")
        d = br.to_dict()
        assert d["success"] is False
        assert d["error"] == "Timeout exceeded"
