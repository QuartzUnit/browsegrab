"""Tests for browsegrab.llm.parse — 5-stage JSON fallback parser."""

import pytest

from browsegrab.llm.parse import VALID_ACTIONS, parse_action_json


class TestStage1Direct:
    """Stage 1: Direct JSON parse."""

    def test_direct_click(self):
        result = parse_action_json('{"action": "click", "ref": "e1"}')
        assert result["action"] == "click"
        assert result["ref"] == "e1"

    def test_direct_navigate(self):
        result = parse_action_json('{"action": "navigate", "url": "https://example.com"}')
        assert result["action"] == "navigate"
        assert result["url"] == "https://example.com"

    def test_direct_type(self):
        result = parse_action_json('{"action": "type", "ref": "e3", "text": "hello", "submit": true}')
        assert result["action"] == "type"
        assert result["text"] == "hello"
        assert result["submit"] is True

    def test_direct_done(self):
        result = parse_action_json('{"action": "done", "result": "Found the answer"}')
        assert result["action"] == "done"
        assert result["result"] == "Found the answer"

    def test_direct_fail(self):
        result = parse_action_json('{"action": "fail", "reason": "Element not found"}')
        assert result["action"] == "fail"


class TestStage2CodeBlock:
    """Stage 2: Code block extraction."""

    def test_json_code_block(self):
        text = '```json\n{"action": "click", "ref": "e5"}\n```'
        result = parse_action_json(text)
        assert result["action"] == "click"
        assert result["ref"] == "e5"

    def test_plain_code_block(self):
        text = '```\n{"action": "scroll", "direction": "down"}\n```'
        result = parse_action_json(text)
        assert result["action"] == "scroll"
        assert result["direction"] == "down"

    def test_code_block_with_surrounding_text(self):
        text = 'Here is the action:\n```json\n{"action": "wait", "ms": 2000}\n```\nDone.'
        result = parse_action_json(text)
        assert result["action"] == "wait"
        assert result["ms"] == 2000


class TestStage3BraceBoundary:
    """Stage 3: Text before/after JSON — brace boundary detection."""

    def test_text_before_json(self):
        text = 'I think {"action": "scroll", "direction": "down"} is best'
        result = parse_action_json(text)
        assert result["action"] == "scroll"
        assert result["direction"] == "down"

    def test_text_after_json(self):
        text = '{"action": "click", "ref": "e1"}\nThat should work.'
        result = parse_action_json(text)
        assert result["action"] == "click"

    def test_lots_of_surrounding_text(self):
        text = (
            "Based on the page structure, I can see a search box. "
            'Let me click it: {"action": "click", "ref": "e7"} '
            "This will open the search interface."
        )
        result = parse_action_json(text)
        assert result["action"] == "click"
        assert result["ref"] == "e7"


class TestStage4Cleanup:
    """Stage 4: Single quotes, trailing commas, unquoted keys."""

    def test_single_quotes(self):
        text = "{'action': 'click', 'ref': 'e2'}"
        result = parse_action_json(text)
        assert result["action"] == "click"
        assert result["ref"] == "e2"

    def test_trailing_comma(self):
        text = '{"action": "go_back",}'
        result = parse_action_json(text)
        assert result["action"] == "go_back"

    def test_unquoted_keys(self):
        text = '{action: "extract", ref: "e4"}'
        result = parse_action_json(text)
        assert result["action"] == "extract"
        assert result["ref"] == "e4"


class TestStage5Regex:
    """Stage 5: Regex extraction from messy text."""

    def test_regex_action_and_ref(self):
        # Malformed JSON that only regex can handle
        text = 'Hmm, I will do "action": "click" on "ref": "e3" now'
        result = parse_action_json(text)
        assert result["action"] == "click"
        assert result["ref"] == "e3"

    def test_regex_extracts_url(self):
        text = 'Let me "action": "navigate" to "url": "https://example.com" please'
        result = parse_action_json(text)
        assert result["action"] == "navigate"
        assert result["url"] == "https://example.com"

    def test_regex_extracts_direction(self):
        text = 'I need to "action": "scroll" with "direction": "up"'
        result = parse_action_json(text)
        assert result["action"] == "scroll"
        assert result["direction"] == "up"


class TestValidActions:
    """All valid action types are accepted; invalid ones rejected."""

    @pytest.mark.parametrize("action", sorted(VALID_ACTIONS))
    def test_all_valid_actions_accepted(self, action):
        result = parse_action_json(f'{{"action": "{action}"}}')
        assert result["action"] == action

    def test_invalid_action_raises(self):
        with pytest.raises(ValueError, match="Cannot parse action"):
            parse_action_json('{"action": "destroy_everything"}')

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Cannot parse action"):
            parse_action_json("")

    def test_no_action_key_raises(self):
        with pytest.raises(ValueError, match="Cannot parse action"):
            parse_action_json('{"ref": "e1", "text": "hello"}')

    def test_random_text_raises(self):
        with pytest.raises(ValueError, match="Cannot parse action"):
            parse_action_json("The weather is nice today.")

    def test_whitespace_stripped(self):
        result = parse_action_json('  \n {"action": "wait", "ms": 500} \n  ')
        assert result["action"] == "wait"
        assert result["ms"] == 500
