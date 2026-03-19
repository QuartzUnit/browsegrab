"""Tests for browsegrab.agent.loop_guard — loop detection and escape."""

from browsegrab.agent.loop_guard import LoopGuard


class TestNoLoop:
    """No loop when actions differ."""

    def test_no_loop_with_different_actions(self):
        lg = LoopGuard()
        lg.record("click", "e1")
        lg.record("scroll", "")
        lg.record("type", "e2")
        assert lg.is_looping() is False

    def test_no_loop_with_insufficient_history(self):
        lg = LoopGuard(window_size=3)
        lg.record("click", "e1")
        lg.record("click", "e1")
        # Only 2 actions, window_size=3 → not enough to detect
        assert lg.is_looping() is False

    def test_no_loop_empty_history(self):
        lg = LoopGuard()
        assert lg.is_looping() is False


class TestSameActionRepeated:
    """Loop: same action repeated N times in a row."""

    def test_same_action_three_times(self):
        lg = LoopGuard(window_size=3)
        lg.record("click", "e1")
        lg.record("click", "e1")
        lg.record("click", "e1")
        assert lg.is_looping() is True

    def test_same_action_name_different_target_not_loop(self):
        lg = LoopGuard(window_size=3)
        lg.record("click", "e1")
        lg.record("click", "e2")
        lg.record("click", "e3")
        # Same action but different targets → different keys → not all same
        assert lg.is_looping() is False


class TestPatternRepetition:
    """Loop: pattern repetition (A-B-A-B)."""

    def test_ab_ab_pattern(self):
        lg = LoopGuard(window_size=2, max_repeats=2)
        lg.record("click", "e1")  # A
        lg.record("scroll", "")   # B
        lg.record("click", "e1")  # A
        lg.record("scroll", "")   # B
        lg.record("click", "e1")  # A
        lg.record("scroll", "")   # B
        assert lg.is_looping() is True

    def test_abc_abc_pattern(self):
        lg = LoopGuard(window_size=3, max_repeats=2)
        lg.record("click", "e1")
        lg.record("type", "e2")
        lg.record("scroll", "")
        lg.record("click", "e1")
        lg.record("type", "e2")
        lg.record("scroll", "")
        lg.record("click", "e1")
        lg.record("type", "e2")
        lg.record("scroll", "")
        assert lg.is_looping() is True


class TestGetEscapeHint:
    """get_escape_hint() content."""

    def test_escape_hint_contains_warning(self):
        lg = LoopGuard(window_size=3)
        lg.record("click", "e1")
        lg.record("click", "e1")
        lg.record("click", "e1")
        hint = lg.get_escape_hint()
        assert "WARNING" in hint
        assert "loop" in hint
        assert "click:e1" in hint

    def test_escape_hint_empty_when_no_history(self):
        lg = LoopGuard()
        assert lg.get_escape_hint() == ""

    def test_escape_hint_suggests_alternatives(self):
        lg = LoopGuard(window_size=2)
        lg.record("scroll", "")
        lg.record("scroll", "")
        hint = lg.get_escape_hint()
        assert "different approach" in hint


class TestReset:
    """reset() clears state."""

    def test_reset_clears_history(self):
        lg = LoopGuard(window_size=3)
        lg.record("click", "e1")
        lg.record("click", "e1")
        lg.record("click", "e1")
        assert lg.is_looping() is True

        lg.reset()
        assert lg.is_looping() is False

    def test_reset_allows_fresh_start(self):
        lg = LoopGuard(window_size=3)
        lg.record("click", "e1")
        lg.record("click", "e1")
        lg.record("click", "e1")
        lg.reset()

        # Record different actions — no loop
        lg.record("navigate", "")
        lg.record("click", "e2")
        lg.record("type", "e3")
        assert lg.is_looping() is False
