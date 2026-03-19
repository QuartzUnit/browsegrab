"""BrowseSession — main orchestrator for agentic browsing.

Combines browser management, AX tree snapshots, LLM planning,
and action execution into a single async session.
"""

from __future__ import annotations

import contextlib
import logging
import time
from types import TracebackType
from typing import Any

from browsegrab.agent.cache import PatternCache
from browsegrab.agent.history import compress_history
from browsegrab.agent.loop_guard import LoopGuard
from browsegrab.browser.actions import click, go_back, navigate, scroll, type_text, wait
from browsegrab.browser.manager import BrowserManager
from browsegrab.browser.snapshot import take_snapshot
from browsegrab.config import BrowseGrabConfig
from browsegrab.dom.compress import compress_dom
from browsegrab.dom.ref_map import RefMap
from browsegrab.llm.base import LLMProvider
from browsegrab.llm.prompt import build_action_prompt
from browsegrab.llm.provider import get_provider
from browsegrab.result import ActionResult, BrowseResult, SnapshotResult, StepRecord

logger = logging.getLogger(__name__)


class BrowseSession:
    """Main orchestrator: URL → browser actions → LLM planning → results.

    Usage::

        async with BrowseSession() as session:
            result = await session.browse("https://example.com", "Find the about page")
            print(result.content)

    Or for manual control::

        async with BrowseSession() as session:
            await session.navigate("https://example.com")
            snap = await session.snapshot()
            await session.click("e2")
    """

    def __init__(
        self,
        config: BrowseGrabConfig | None = None,
        manager: BrowserManager | None = None,
    ) -> None:
        self.config = config or BrowseGrabConfig()
        self._manager = manager
        self._owns_manager = manager is None
        self._page = None
        self._ref_map = RefMap()
        self._llm: LLMProvider | None = None
        self._cache = PatternCache(self.config.agent.cache_dir) if self.config.agent.enable_cache else None
        self._loop_guard = LoopGuard(window_size=self.config.agent.loop_detection_window)
        self._steps: list[StepRecord] = []
        self._total_tokens = 0

    @property
    def manager(self) -> BrowserManager:
        if self._manager is None:
            self._manager = BrowserManager(self.config.browser)
        return self._manager

    @property
    def llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = get_provider(self.config.llm)
        return self._llm

    async def _ensure_page(self):
        """Ensure a browser page is available."""
        if self._page is None or self._page.is_closed():
            self._page = await self.manager.new_page()
        return self._page

    # ── Manual control API ──────────────────────────────────────────

    async def navigate(self, url: str, **expectation: Any) -> ActionResult:
        """Navigate to a URL."""
        page = await self._ensure_page()
        return await navigate(page, url, self._ref_map, expectation=expectation or None)

    async def snapshot(self) -> SnapshotResult:
        """Take an accessibility tree snapshot of the current page."""
        page = await self._ensure_page()
        return await take_snapshot(page, self._ref_map, self.config.snapshot)

    async def click(self, ref: str, **expectation: Any) -> ActionResult:
        """Click an element by ref ID."""
        page = await self._ensure_page()
        return await click(page, ref, self._ref_map, expectation=expectation or None)

    async def type(self, ref: str, text: str, clear: bool = True, submit: bool = False, **expectation: Any) -> ActionResult:
        """Type text into an element."""
        page = await self._ensure_page()
        return await type_text(page, ref, text, self._ref_map, clear=clear, submit=submit, expectation=expectation or None)

    async def scroll(self, direction: str = "down", amount: int = 500, ref: str | None = None, **expectation: Any) -> ActionResult:
        """Scroll the page or element."""
        page = await self._ensure_page()
        return await scroll(page, direction, self._ref_map, amount=amount, ref=ref, expectation=expectation or None)

    async def go_back(self, **expectation: Any) -> ActionResult:
        """Navigate back."""
        page = await self._ensure_page()
        return await go_back(page, self._ref_map, expectation=expectation or None)

    async def wait(self, ms: int = 1000, selector: str | None = None, state: str = "visible") -> ActionResult:
        """Wait for time or element."""
        page = await self._ensure_page()
        return await wait(page, ms=ms, selector=selector, state=state)

    async def extract_content(self, max_length: int | None = None, scope: str | None = None) -> str:
        """Extract page content as compressed DOM (AX tree + optional MarkGrab)."""
        page = await self._ensure_page()
        return await compress_dom(
            page,
            self._ref_map,
            self.config.snapshot,
            include_content=True,
            scope_selector=scope,
        )

    # ── Agentic browsing API ────────────────────────────────────────

    async def browse(
        self,
        url: str,
        objective: str,
        max_steps: int | None = None,
    ) -> BrowseResult:
        """Agentic browsing: LLM plans and executes actions to achieve an objective.

        Args:
            url: Starting URL.
            objective: What the agent should accomplish.
            max_steps: Override max steps (default from config).

        Returns:
            BrowseResult with extracted content and action history.
        """
        max_steps = max_steps or self.config.agent.max_steps
        start_time = time.monotonic()
        self._steps.clear()
        self._total_tokens = 0
        self._loop_guard.reset()

        page = await self._ensure_page()

        # Navigate to starting URL
        nav_result = await navigate(page, url, self._ref_map)
        if not nav_result.success:
            return BrowseResult(
                success=False,
                url=url,
                error=nav_result.error or "Navigation failed",
                processing_time_ms=(time.monotonic() - start_time) * 1000,
            )

        self._steps.append(StepRecord(step=0, action="navigate", target=url, url=page.url))

        # Check cache for known patterns
        cached_hint = ""
        if self._cache:
            cached_hint = self._cache.get_hint(url, objective)

        # Agent loop
        for step_num in range(1, max_steps + 1):
            # Get compressed DOM
            dom_context = await compress_dom(page, self._ref_map, self.config.snapshot)

            # Check for loops
            loop_hint = ""
            if self._loop_guard.is_looping():
                loop_hint = self._loop_guard.get_escape_hint()
                logger.warning("Loop detected at step %d", step_num)

            # Build prompt and get LLM action
            history_text = compress_history(self._steps, self.config.agent.history_max_entries)
            context = dom_context
            if loop_hint:
                context = f"{loop_hint}\n\n{context}"

            messages = build_action_prompt(objective, context, history_text, cached_hint)

            try:
                response = await self.llm.chat(
                    messages,
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens,
                )
            except Exception as e:
                logger.error("LLM call failed at step %d: %s", step_num, e)
                return BrowseResult(
                    success=False,
                    url=page.url,
                    title=await page.title(),
                    steps=self._steps,
                    total_steps=step_num,
                    total_tokens=self._total_tokens,
                    error=f"LLM error: {e}",
                    processing_time_ms=(time.monotonic() - start_time) * 1000,
                )

            # Parse LLM response
            from browsegrab.llm.parse import parse_action_json

            try:
                action_dict = parse_action_json(response)
            except ValueError as e:
                logger.warning("Cannot parse LLM response at step %d: %s", step_num, e)
                self._steps.append(StepRecord(
                    step=step_num, action="parse_error", summary=str(e)[:100], success=False,
                ))
                continue

            action_name = action_dict.get("action", "")
            self._loop_guard.record(action_name, action_dict.get("ref", action_dict.get("url", "")))

            # Handle terminal actions
            if action_name == "done":
                result_text = action_dict.get("result", "")
                # Extract final content
                content = await compress_dom(page, self._ref_map, self.config.snapshot, include_content=True)
                snap = await take_snapshot(page, self._ref_map, self.config.snapshot)

                if self._cache:
                    self._cache.store(url, objective, [
                        {"action": s.action, "ref": s.target} for s in self._steps
                    ])

                return BrowseResult(
                    success=True,
                    url=page.url,
                    title=snap.title,
                    content=result_text or content,
                    snapshot=snap.tree_text,
                    steps=self._steps,
                    total_steps=step_num,
                    total_tokens=self._total_tokens,
                    processing_time_ms=(time.monotonic() - start_time) * 1000,
                )

            if action_name == "fail":
                return BrowseResult(
                    success=False,
                    url=page.url,
                    title=await page.title(),
                    steps=self._steps,
                    total_steps=step_num,
                    total_tokens=self._total_tokens,
                    error=action_dict.get("reason", "Agent reported failure"),
                    processing_time_ms=(time.monotonic() - start_time) * 1000,
                )

            # Execute the action
            action_result = await self._execute_action(page, action_dict)
            self._steps.append(StepRecord(
                step=step_num,
                action=action_name,
                target=action_result.target,
                url=action_result.url,
                success=action_result.success,
                summary=action_result.error or "",
            ))
            self._total_tokens += action_result.token_estimate

        # Max steps reached
        content = await compress_dom(page, self._ref_map, self.config.snapshot, include_content=True)
        return BrowseResult(
            success=False,
            url=page.url,
            title=await page.title(),
            content=content,
            steps=self._steps,
            total_steps=max_steps,
            total_tokens=self._total_tokens,
            error=f"Max steps ({max_steps}) reached without completing objective",
            processing_time_ms=(time.monotonic() - start_time) * 1000,
        )

    async def _execute_action(self, page, action_dict: dict[str, Any]) -> ActionResult:
        """Execute a parsed action dict."""
        action_name = action_dict["action"]
        exp = {"include_snapshot": True}

        if action_name == "click":
            return await click(page, action_dict.get("ref", ""), self._ref_map, expectation=exp)

        if action_name == "type":
            return await type_text(
                page,
                action_dict.get("ref", ""),
                action_dict.get("text", ""),
                self._ref_map,
                submit=action_dict.get("submit", False),
                expectation=exp,
            )

        if action_name == "scroll":
            return await scroll(
                page,
                action_dict.get("direction", "down"),
                self._ref_map,
                amount=action_dict.get("amount", 500),
                expectation=exp,
            )

        if action_name == "navigate":
            return await navigate(page, action_dict.get("url", ""), self._ref_map, expectation=exp)

        if action_name == "go_back":
            return await go_back(page, self._ref_map, expectation=exp)

        if action_name == "wait":
            return await wait(page, ms=action_dict.get("ms", 1000), selector=action_dict.get("selector"))

        if action_name == "extract":
            content = await compress_dom(page, self._ref_map, self.config.snapshot, include_content=True)
            return ActionResult(success=True, action="extract", url=page.url, title=await page.title(), content=content)

        return ActionResult(success=False, action=action_name, error=f"Unknown action: {action_name}")

    # ── Lifecycle ───────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the session."""
        if self._page and not self._page.is_closed():
            with contextlib.suppress(Exception):
                await self._page.context.close()
            self._page = None
        if self._owns_manager and self._manager:
            await self._manager.close()
            self._manager = None

    async def __aenter__(self) -> BrowseSession:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
