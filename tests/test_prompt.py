"""Tests for browsegrab.llm.prompt module."""

from __future__ import annotations

from browsegrab.llm.prompt import SYSTEM_PROMPT, build_action_prompt

# ── SYSTEM_PROMPT content ─────────────────────────────────────


class TestSystemPrompt:
    def test_contains_required_actions(self):
        """SYSTEM_PROMPT must mention all core action types."""
        required_actions = ["click", "type", "scroll", "navigate", "go_back", "wait", "extract", "done", "fail"]
        for action in required_actions:
            assert action in SYSTEM_PROMPT, f"Missing action '{action}' in SYSTEM_PROMPT"

    def test_contains_ref_instruction(self):
        """Prompt must instruct the LLM to use ref IDs."""
        assert "ref" in SYSTEM_PROMPT.lower()

    def test_json_only_instruction(self):
        """Prompt must instruct JSON-only responses."""
        assert "JSON" in SYSTEM_PROMPT


# ── build_action_prompt() ─────────────────────────────────────


class TestBuildActionPrompt:
    def test_basic_structure(self):
        """Returns [system, user] messages with correct roles."""
        messages = build_action_prompt(
            objective="Find the about page",
            snapshot="- heading ...\n- link ...",
        )

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == SYSTEM_PROMPT
        assert messages[1]["role"] == "user"
        assert "Find the about page" in messages[1]["content"]
        assert "- heading" in messages[1]["content"]

    def test_with_cached_hint(self):
        """cached_hint text appears in the user message."""
        messages = build_action_prompt(
            objective="Search for Python",
            snapshot="...",
            cached_hint="Click e3 then type 'Python'",
        )

        user_content = messages[1]["content"]
        assert "Click e3 then type 'Python'" in user_content
        assert "Hint" in user_content

    def test_with_history(self):
        """History text appears in the user message."""
        messages = build_action_prompt(
            objective="Navigate",
            snapshot="...",
            history="Step 1: navigate https://example.com\nStep 2: click e2",
        )

        user_content = messages[1]["content"]
        assert "Step 1: navigate" in user_content
        assert "Previous actions" in user_content

    def test_without_history_or_hint(self):
        """When history and cached_hint are empty, neither section appears."""
        messages = build_action_prompt(
            objective="Test",
            snapshot="snapshot text",
            history="",
            cached_hint="",
        )

        user_content = messages[1]["content"]
        assert "Hint" not in user_content
        assert "Previous actions" not in user_content
