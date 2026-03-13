import unittest
from types import SimpleNamespace

from aiops.cache.memory_ttl import MemoryTTLCache
from aiops.cache.factory import get_process_cache
from aiops.skills.global_registry import _reset_global_skill_registry_for_tests
from aiops.workflows.router_workflow import make_skill_orchestration_node


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


class TestMemoryTTLCache(unittest.TestCase):
    def setUp(self) -> None:
        _reset_global_skill_registry_for_tests()
        get_process_cache.cache_clear()

    def test_cache_hit(self) -> None:
        clock = FakeClock()
        cache: MemoryTTLCache[int] = MemoryTTLCache(default_ttl_sec=10.0, now=clock)
        cache.set("k1", 123)
        self.assertEqual(cache.get("k1"), 123)
        stats = cache.stats()
        self.assertEqual(stats.hits, 1)
        self.assertEqual(stats.misses, 0)

    def test_cache_expired(self) -> None:
        clock = FakeClock()
        cache: MemoryTTLCache[str] = MemoryTTLCache(default_ttl_sec=2.0, now=clock)
        cache.set("k1", "v1")
        clock.advance(2.0)
        self.assertEqual(cache.get("k1", "fallback"), "fallback")
        stats = cache.stats()
        self.assertEqual(stats.expired, 1)
        self.assertEqual(stats.misses, 1)

    def test_skill_orchestration_cache_enabled(self) -> None:
        settings = SimpleNamespace(cache=SimpleNamespace(enabled=True, default_ttl_sec=60.0, max_entries=128))
        node = make_skill_orchestration_node(settings)
        cache = get_process_cache(default_ttl_sec=60.0, max_entries=128)
        cache.clear()

        node({"query": "cpu usage", "classifications": [], "results": [], "final_answer": "", "context": {}})
        node({"query": "cpu usage", "classifications": [], "results": [], "final_answer": "", "context": {}})

        stats = cache.stats()
        self.assertGreaterEqual(stats.hits, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
