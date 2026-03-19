"""Loop detection and escape for agent action sequences.

Detects when the agent is stuck repeating the same actions
and forces an alternative approach or graceful failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LoopGuard:
    """Detects repeated action patterns and prevents infinite loops."""

    window_size: int = 3
    max_repeats: int = 2
    _history: list[str] = field(default_factory=list)
    _repeat_count: int = 0

    def record(self, action: str, target: str = "") -> None:
        """Record an action for loop detection."""
        key = f"{action}:{target}"
        self._history.append(key)

    def is_looping(self) -> bool:
        """Check if the recent actions form a repeating pattern.

        Detects:
        1. Same action repeated N times in a row
        2. Pattern repetition (e.g. A-B-A-B)
        """
        if len(self._history) < self.window_size:
            return False

        recent = self._history[-self.window_size :]

        # Check 1: All same action
        if len(set(recent)) == 1:
            return True

        # Check 2: Pattern repetition (AB-AB or ABC-ABC)
        history_len = len(self._history)
        for pattern_len in range(1, self.window_size + 1):
            if history_len < pattern_len * (self.max_repeats + 1):
                continue
            pattern = self._history[-pattern_len:]
            repeated = True
            for i in range(1, self.max_repeats + 1):
                start = -(pattern_len * (i + 1))
                end = -(pattern_len * i)
                segment = self._history[start:] if end == 0 else self._history[start:end]
                if segment != pattern:
                    repeated = False
                    break
            if repeated:
                return True

        return False

    def get_escape_hint(self) -> str:
        """Generate a hint for the LLM to break out of the loop."""
        if not self._history:
            return ""

        recent = self._history[-self.window_size :]
        actions = ", ".join(recent)
        return (
            f"WARNING: You are stuck in a loop ({actions}). "
            "Try a completely different approach: "
            "scroll to find new elements, navigate to a different page, "
            "or report failure if the objective cannot be achieved."
        )

    def reset(self) -> None:
        """Reset the loop guard state."""
        self._history.clear()
        self._repeat_count = 0
