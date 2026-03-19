"""Success pattern cache — domain-based file cache.

Stores successful action sequences per domain so that repeated
workflows can skip LLM calls entirely.

Cache location: ~/.cache/browsegrab/patterns.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class PatternCache:
    """Domain-based success pattern cache."""

    def __init__(self, cache_dir: str = "~/.cache/browsegrab") -> None:
        self._cache_dir = Path(cache_dir).expanduser()
        self._cache_file = self._cache_dir / "patterns.json"
        self._data: dict[str, list[dict]] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Lazily load cache from disk."""
        if self._loaded:
            return
        self._loaded = True
        if self._cache_file.exists():
            try:
                self._data = json.loads(self._cache_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.debug("Cache load failed: %s", e)
                self._data = {}

    def _save(self) -> None:
        """Persist cache to disk."""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache_file.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.debug("Cache save failed: %s", e)

    @staticmethod
    def _domain_key(url: str) -> str:
        """Extract domain from URL for cache key."""
        try:
            return urlparse(url).netloc or "unknown"
        except Exception:
            return "unknown"

    def lookup(self, url: str, objective: str) -> list[dict] | None:
        """Look up cached action sequence for a domain + objective.

        Args:
            url: Target URL.
            objective: User's goal description.

        Returns:
            List of action dicts if found, None otherwise.
        """
        self._ensure_loaded()
        domain = self._domain_key(url)
        entries = self._data.get(domain, [])
        for entry in entries:
            if self._objective_match(entry.get("objective", ""), objective):
                logger.debug("Cache hit for %s: %s", domain, objective[:50])
                return entry.get("actions", [])
        return None

    def store(self, url: str, objective: str, actions: list[dict]) -> None:
        """Store a successful action sequence.

        Args:
            url: Target URL.
            objective: User's goal description.
            actions: List of action dicts that achieved the goal.
        """
        self._ensure_loaded()
        domain = self._domain_key(url)
        if domain not in self._data:
            self._data[domain] = []

        # Deduplicate: remove existing entry for same objective
        self._data[domain] = [e for e in self._data[domain] if not self._objective_match(e.get("objective", ""), objective)]

        self._data[domain].append({
            "objective": objective,
            "actions": actions,
        })

        # Limit entries per domain
        if len(self._data[domain]) > 20:
            self._data[domain] = self._data[domain][-20:]

        self._save()

    def get_hint(self, url: str, objective: str) -> str:
        """Get a compact hint string from cached patterns for LLM context.

        Returns empty string if no cache hit.
        """
        actions = self.lookup(url, objective)
        if not actions:
            return ""

        hints = []
        for i, a in enumerate(actions[:5], 1):
            action = a.get("action", "?")
            target = a.get("ref", a.get("url", a.get("text", "")))
            hints.append(f"{i}. {action} → {target}")
        return "Previously successful steps:\n" + "\n".join(hints)

    @staticmethod
    def _objective_match(cached: str, query: str) -> bool:
        """Simple objective matching — exact match after normalization."""
        return cached.strip().lower() == query.strip().lower()

    def clear(self, domain: str | None = None) -> None:
        """Clear cache for a specific domain or all."""
        self._ensure_loaded()
        if domain:
            self._data.pop(domain, None)
        else:
            self._data.clear()
        self._save()
