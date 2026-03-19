"""System prompts for LLM-driven browser actions.

Compact prompts designed for local LLMs (8B-35B parameters).
~400 tokens system prompt target.
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are a browser automation agent. You control a web browser to achieve the user's objective.

## Available Actions (respond with JSON)

- {"action": "click", "ref": "eN"} — Click element with ref ID
- {"action": "type", "ref": "eN", "text": "..."} — Type text (clears field first)
- {"action": "type", "ref": "eN", "text": "...", "submit": true} — Type and press Enter
- {"action": "scroll", "direction": "down|up"} — Scroll page
- {"action": "navigate", "url": "..."} — Go to URL
- {"action": "go_back"} — Browser back button
- {"action": "wait", "ms": 1000} — Wait for content to load
- {"action": "extract"} — Extract page content as markdown
- {"action": "done", "result": "..."} — Task complete, report result
- {"action": "fail", "reason": "..."} — Cannot complete task

## Rules

1. Use ref IDs (e1, e2, ...) from the accessibility tree to target elements
2. One action per response — JSON only, no explanation
3. After typing in search, usually submit with Enter
4. Scroll if target element is not visible
5. If stuck in a loop, try a different approach or report failure

## Response Format

Respond with ONLY a JSON object. No markdown, no explanation."""


PLANNING_PROMPT = """You are a browser automation planner. Given a page snapshot, decide the SINGLE best next action.

The page snapshot shows:
- Interactive elements with ref IDs: [ref=eN]
- Element roles: link, button, textbox, heading, etc.
- Element names in quotes

Respond with ONLY a JSON object for the next action."""


def build_action_prompt(
    objective: str,
    snapshot: str,
    history: str = "",
    cached_hint: str = "",
) -> list[dict[str, str]]:
    """Build the message list for action planning.

    Args:
        objective: User's goal.
        snapshot: Current page AX tree snapshot.
        history: Compressed action history.
        cached_hint: Optional hint from success pattern cache.

    Returns:
        List of message dicts for LLM chat.
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    user_parts: list[str] = [f"Objective: {objective}"]

    if cached_hint:
        user_parts.append(f"\nHint (from previous successful run):\n{cached_hint}")

    user_parts.append(f"\nCurrent page:\n{snapshot}")

    if history:
        user_parts.append(f"\nPrevious actions:\n{history}")

    user_parts.append("\nWhat is the next action? Respond with JSON only.")

    messages.append({"role": "user", "content": "\n".join(user_parts)})
    return messages
