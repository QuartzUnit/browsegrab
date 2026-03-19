"""5-stage JSON fallback parser for LLM action responses.

Stages:
1. Direct JSON parse
2. Code block extraction (```json ... ```)
3. Brace boundary detection
4. Key-value cleanup + retry
5. Regex extraction of action/ref fields
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Valid action names
VALID_ACTIONS = frozenset({
    "click",
    "type",
    "scroll",
    "navigate",
    "go_back",
    "wait",
    "extract",
    "done",
    "fail",
})


def parse_action_json(text: str) -> dict[str, Any]:
    """Parse LLM response into an action dict using 5-stage fallback.

    Args:
        text: Raw LLM response text.

    Returns:
        Parsed action dict with at least an "action" key.

    Raises:
        ValueError: If all 5 stages fail to extract a valid action.
    """
    text = text.strip()

    # Stage 1: Direct JSON parse
    result = _stage1_direct(text)
    if result:
        return result

    # Stage 2: Code block extraction
    result = _stage2_code_block(text)
    if result:
        return result

    # Stage 3: Brace boundary detection
    result = _stage3_brace_boundary(text)
    if result:
        return result

    # Stage 4: Key-value cleanup
    result = _stage4_cleanup(text)
    if result:
        return result

    # Stage 5: Regex extraction
    result = _stage5_regex(text)
    if result:
        return result

    raise ValueError(f"Cannot parse action from LLM response: {text[:200]}")


def _validate(data: Any) -> dict[str, Any] | None:
    """Validate parsed data is a valid action dict."""
    if not isinstance(data, dict):
        return None
    action = data.get("action", "")
    if action not in VALID_ACTIONS:
        return None
    return data


def _stage1_direct(text: str) -> dict[str, Any] | None:
    """Stage 1: Direct JSON parse."""
    try:
        data = json.loads(text)
        return _validate(data)
    except (json.JSONDecodeError, ValueError):
        return None


def _stage2_code_block(text: str) -> dict[str, Any] | None:
    """Stage 2: Extract JSON from markdown code blocks."""
    patterns = [
        r"```json\s*\n?(.*?)\n?\s*```",
        r"```\s*\n?(.*?)\n?\s*```",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                return _validate(data)
            except (json.JSONDecodeError, ValueError):
                continue
    return None


def _stage3_brace_boundary(text: str) -> dict[str, Any] | None:
    """Stage 3: Find outermost { ... } and parse."""
    start = text.find("{")
    if start == -1:
        return None

    # Find matching closing brace
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    data = json.loads(text[start : i + 1])
                    return _validate(data)
                except (json.JSONDecodeError, ValueError):
                    return None
    return None


def _stage4_cleanup(text: str) -> dict[str, Any] | None:
    """Stage 4: Clean up common JSON issues and retry."""
    # Extract the JSON-like portion
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start : end + 1]

    # Fix common issues
    # Single quotes → double quotes
    candidate = candidate.replace("'", '"')
    # Trailing commas before }
    candidate = re.sub(r",\s*}", "}", candidate)
    # Trailing commas before ]
    candidate = re.sub(r",\s*]", "]", candidate)
    # Unquoted keys
    candidate = re.sub(r"(\{|,)\s*(\w+)\s*:", r'\1 "\2":', candidate)

    try:
        data = json.loads(candidate)
        return _validate(data)
    except (json.JSONDecodeError, ValueError):
        return None


def _stage5_regex(text: str) -> dict[str, Any] | None:
    """Stage 5: Regex extraction of action and ref fields."""
    # Try to extract action
    action_match = re.search(r'"action"\s*:\s*"(\w+)"', text)
    if not action_match:
        return None

    action = action_match.group(1)
    if action not in VALID_ACTIONS:
        return None

    result: dict[str, Any] = {"action": action}

    # Extract ref
    ref_match = re.search(r'"ref"\s*:\s*"(e\d+)"', text)
    if ref_match:
        result["ref"] = ref_match.group(1)

    # Extract text
    text_match = re.search(r'"text"\s*:\s*"([^"]*)"', text)
    if text_match:
        result["text"] = text_match.group(1)

    # Extract url
    url_match = re.search(r'"url"\s*:\s*"([^"]*)"', text)
    if url_match:
        result["url"] = url_match.group(1)

    # Extract direction
    dir_match = re.search(r'"direction"\s*:\s*"(\w+)"', text)
    if dir_match:
        result["direction"] = dir_match.group(1)

    # Extract submit
    submit_match = re.search(r'"submit"\s*:\s*(true|false)', text)
    if submit_match:
        result["submit"] = submit_match.group(1) == "true"

    # Extract result (for done action)
    result_match = re.search(r'"result"\s*:\s*"([^"]*)"', text)
    if result_match:
        result["result"] = result_match.group(1)

    # Extract reason (for fail action)
    reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', text)
    if reason_match:
        result["reason"] = reason_match.group(1)

    # Extract ms (for wait action)
    ms_match = re.search(r'"ms"\s*:\s*(\d+)', text)
    if ms_match:
        result["ms"] = int(ms_match.group(1))

    return result
