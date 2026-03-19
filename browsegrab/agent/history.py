"""Action history compression for LLM context efficiency.

Strategy: keep first entry + summarize repeated patterns + keep last N entries.
Max entries configurable (default 5). ~100-300 tokens budget.
"""

from __future__ import annotations

from browsegrab.result import StepRecord


def compress_history(steps: list[StepRecord], max_entries: int = 5) -> str:
    """Compress action history into a compact string for LLM context.

    Format:
    - First entry (always kept for context)
    - Middle entries summarized if > max_entries
    - Last N entries (most recent, fully detailed)

    Args:
        steps: Full list of step records.
        max_entries: Maximum entries to include.

    Returns:
        Compressed history string.
    """
    if not steps:
        return "(no actions taken yet)"

    if len(steps) <= max_entries:
        return "\n".join(_format_step(s) for s in steps)

    lines: list[str] = []

    # Always include first step
    lines.append(_format_step(steps[0]))

    # Summarize middle
    middle = steps[1 : -(max_entries - 1)]
    if middle:
        summary = _summarize_middle(middle)
        lines.append(summary)

    # Include last N-1 steps
    for step in steps[-(max_entries - 1) :]:
        lines.append(_format_step(step))

    return "\n".join(lines)


def _format_step(step: StepRecord) -> str:
    """Format a single step into a compact string."""
    parts = [f"Step {step.step}: {step.action}"]
    if step.target:
        parts.append(f" → {step.target}")
    if step.url:
        parts.append(f" @ {step.url}")
    if not step.success:
        parts.append(" [FAILED]")
    if step.summary:
        parts.append(f" ({step.summary})")
    return "".join(parts)


def _summarize_middle(steps: list[StepRecord]) -> str:
    """Summarize a sequence of middle steps into one line."""
    action_counts: dict[str, int] = {}
    for step in steps:
        action_counts[step.action] = action_counts.get(step.action, 0) + 1

    parts = [f"{count}x {action}" for action, count in action_counts.items()]
    return f"  ... ({len(steps)} steps: {', '.join(parts)})"
