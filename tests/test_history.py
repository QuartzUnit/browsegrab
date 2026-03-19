"""Tests for browsegrab.agent.history — action history compression."""

from browsegrab.agent.history import compress_history
from browsegrab.result import StepRecord


class TestEmptyHistory:
    """Empty history edge case."""

    def test_empty_list(self):
        assert compress_history([]) == "(no actions taken yet)"


class TestWithinMaxEntries:
    """History within max_entries — no compression needed."""

    def test_single_step(self):
        steps = [StepRecord(step=1, action="navigate", url="https://example.com")]
        result = compress_history(steps)
        assert "Step 1: navigate" in result
        assert "@ https://example.com" in result

    def test_exactly_max_entries(self):
        steps = [
            StepRecord(step=i, action="click", target=f"e{i}")
            for i in range(1, 6)
        ]
        result = compress_history(steps, max_entries=5)
        lines = result.strip().split("\n")
        assert len(lines) == 5
        for i in range(1, 6):
            assert f"Step {i}: click" in result

    def test_under_max_entries(self):
        steps = [
            StepRecord(step=1, action="navigate", url="https://example.com"),
            StepRecord(step=2, action="click", target="e3"),
        ]
        result = compress_history(steps, max_entries=5)
        lines = result.strip().split("\n")
        assert len(lines) == 2


class TestCompression:
    """History exceeding max_entries — should compress middle."""

    def test_compression_keeps_first_and_last(self):
        steps = [
            StepRecord(step=1, action="navigate", url="https://start.com"),
            StepRecord(step=2, action="click", target="e1"),
            StepRecord(step=3, action="click", target="e2"),
            StepRecord(step=4, action="scroll"),
            StepRecord(step=5, action="click", target="e3"),
            StepRecord(step=6, action="type", target="e4"),
            StepRecord(step=7, action="click", target="e5"),
            StepRecord(step=8, action="extract", target="e6"),
        ]
        result = compress_history(steps, max_entries=3)
        lines = result.strip().split("\n")

        # First line: step 1 (always kept)
        assert "Step 1: navigate" in lines[0]
        # Last two lines: steps 7 and 8 (last N-1=2 entries)
        assert "Step 7: click" in lines[-2]
        assert "Step 8: extract" in lines[-1]
        # Middle line: summary
        assert "..." in result
        assert "5 steps" in result

    def test_compression_summary_counts_actions(self):
        steps = [
            StepRecord(step=1, action="navigate"),
            StepRecord(step=2, action="click", target="e1"),
            StepRecord(step=3, action="click", target="e2"),
            StepRecord(step=4, action="scroll"),
            StepRecord(step=5, action="click", target="e3"),
            StepRecord(step=6, action="done"),
        ]
        result = compress_history(steps, max_entries=3)
        # Middle = steps 2,3,4 => 3x actions: 2x click, 1x scroll
        assert "3 steps" in result
        assert "2x click" in result
        assert "1x scroll" in result


class TestStepFormatting:
    """_format_step edge cases."""

    def test_failed_step(self):
        steps = [StepRecord(step=1, action="click", target="e5", success=False)]
        result = compress_history(steps)
        assert "[FAILED]" in result

    def test_step_with_summary(self):
        steps = [StepRecord(step=1, action="extract", summary="Got 3 results")]
        result = compress_history(steps)
        assert "(Got 3 results)" in result

    def test_step_with_all_fields(self):
        steps = [StepRecord(
            step=1,
            action="click",
            target="e1",
            url="https://example.com",
            summary="opened menu",
            success=True,
        )]
        result = compress_history(steps)
        assert "Step 1: click" in result
        assert "e1" in result
        assert "@ https://example.com" in result
        assert "(opened menu)" in result
        assert "[FAILED]" not in result
