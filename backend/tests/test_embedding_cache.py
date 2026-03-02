"""Tests for the embedding LRU cache."""

import pytest
from backend.app.retrieval.search import EmbeddingCache


class TestEmbeddingCache:

    def test_cache_miss_returns_none(self):
        cache = EmbeddingCache(max_size=10)
        assert cache.get("nonexistent") is None

    def test_cache_hit_after_put(self):
        cache = EmbeddingCache(max_size=10)
        vec = [0.1, 0.2, 0.3]
        cache.put("query1", vec)
        assert cache.get("query1") == vec

    def test_evicts_oldest_when_full(self):
        cache = EmbeddingCache(max_size=2)
        cache.put("a", [1.0])
        cache.put("b", [2.0])
        cache.put("c", [3.0])  # Should evict "a"
        assert cache.get("a") is None
        assert cache.get("b") == [2.0]
        assert cache.get("c") == [3.0]

    def test_access_refreshes_lru_order(self):
        cache = EmbeddingCache(max_size=2)
        cache.put("a", [1.0])
        cache.put("b", [2.0])
        cache.get("a")  # Access "a" to make it most recent
        cache.put("c", [3.0])  # Should evict "b", not "a"
        assert cache.get("a") == [1.0]
        assert cache.get("b") is None
        assert cache.get("c") == [3.0]

    def test_tracks_hit_miss_counts(self):
        cache = EmbeddingCache(max_size=10)
        cache.put("a", [1.0])
        cache.get("a")
        cache.get("a")
        cache.get("missing")
        assert cache.hits == 2
        assert cache.misses == 1

    def test_duplicate_put_updates_value(self):
        cache = EmbeddingCache(max_size=10)
        cache.put("a", [1.0])
        cache.put("a", [2.0])
        assert cache.get("a") == [2.0]

    def test_default_max_size_256(self):
        cache = EmbeddingCache()
        assert cache._max_size == 256
