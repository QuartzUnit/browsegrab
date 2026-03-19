"""Tests for browsegrab.agent.cache — domain-based success pattern cache."""

import json

from browsegrab.agent.cache import PatternCache


class TestStoreAndLookup:
    """Store + lookup round-trip."""

    def test_store_and_lookup_success(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        actions = [{"action": "click", "ref": "e1"}, {"action": "type", "ref": "e2", "text": "hello"}]
        cache.store("https://example.com/page", "Fill the form", actions)

        result = cache.lookup("https://example.com/page", "Fill the form")
        assert result == actions

    def test_lookup_miss_returns_none(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        assert cache.lookup("https://example.com", "Do something") is None

    def test_lookup_wrong_objective_returns_none(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        cache.store("https://example.com", "Login", [{"action": "click", "ref": "e1"}])
        assert cache.lookup("https://example.com", "Logout") is None

    def test_objective_match_case_insensitive(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        cache.store("https://example.com", "Search for NEWS", [{"action": "click", "ref": "e1"}])
        result = cache.lookup("https://example.com", "  search for news  ")
        assert result is not None
        assert result[0]["action"] == "click"


class TestGetHint:
    """get_hint() formatting."""

    def test_get_hint_format(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        actions = [
            {"action": "click", "ref": "e1"},
            {"action": "type", "ref": "e2", "text": "query"},
            {"action": "click", "ref": "e3"},
        ]
        cache.store("https://example.com", "Search", actions)
        hint = cache.get_hint("https://example.com", "Search")
        assert hint.startswith("Previously successful steps:")
        assert "1. click" in hint
        assert "2. type" in hint
        assert "3. click" in hint

    def test_get_hint_empty_on_miss(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        assert cache.get_hint("https://nope.com", "Nothing") == ""

    def test_get_hint_truncates_to_5_steps(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        actions = [{"action": "click", "ref": f"e{i}"} for i in range(1, 10)]
        cache.store("https://example.com", "Big task", actions)
        hint = cache.get_hint("https://example.com", "Big task")
        # Only first 5 steps should appear
        assert "5. click" in hint
        assert "6. click" not in hint


class TestDomainKey:
    """Domain key extraction."""

    def test_domain_extracted_from_url(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        cache.store("https://www.google.com/search?q=test", "Search", [{"action": "click"}])
        # Same domain, different path
        result = cache.lookup("https://www.google.com/other", "Search")
        assert result is not None

    def test_different_domains_isolated(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        cache.store("https://google.com", "Search", [{"action": "click"}])
        assert cache.lookup("https://bing.com", "Search") is None

    def test_invalid_url_uses_unknown(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        # _domain_key returns "unknown" for non-URL strings
        cache.store("not-a-url", "Something", [{"action": "done"}])
        result = cache.lookup("also-not-a-url", "Something")
        # Both resolve to "unknown" domain
        assert result is not None


class TestPersistence:
    """File persistence using tmp_path."""

    def test_cache_persists_to_file(self, tmp_path):
        cache1 = PatternCache(cache_dir=str(tmp_path))
        cache1.store("https://example.com", "Test", [{"action": "click", "ref": "e1"}])

        # New instance reads from the same file
        cache2 = PatternCache(cache_dir=str(tmp_path))
        result = cache2.lookup("https://example.com", "Test")
        assert result is not None
        assert result[0]["ref"] == "e1"

    def test_cache_file_is_valid_json(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        cache.store("https://example.com", "Test", [{"action": "done"}])
        cache_file = tmp_path / "patterns.json"
        assert cache_file.exists()
        data = json.loads(cache_file.read_text())
        assert isinstance(data, dict)
        assert "example.com" in data


class TestClear:
    """clear() functionality."""

    def test_clear_all(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        cache.store("https://a.com", "X", [{"action": "click"}])
        cache.store("https://b.com", "Y", [{"action": "scroll"}])
        cache.clear()
        assert cache.lookup("https://a.com", "X") is None
        assert cache.lookup("https://b.com", "Y") is None

    def test_clear_single_domain(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        cache.store("https://a.com", "X", [{"action": "click"}])
        cache.store("https://b.com", "Y", [{"action": "scroll"}])
        cache.clear(domain="a.com")
        assert cache.lookup("https://a.com", "X") is None
        assert cache.lookup("https://b.com", "Y") is not None

    def test_store_deduplicates_same_objective(self, tmp_path):
        cache = PatternCache(cache_dir=str(tmp_path))
        cache.store("https://example.com", "Login", [{"action": "click", "ref": "e1"}])
        cache.store("https://example.com", "Login", [{"action": "click", "ref": "e99"}])
        result = cache.lookup("https://example.com", "Login")
        # Should have the updated version
        assert result[0]["ref"] == "e99"
