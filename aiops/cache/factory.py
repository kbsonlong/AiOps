from __future__ import annotations

from functools import lru_cache

from .memory_ttl import MemoryTTLCache


@lru_cache(maxsize=8)
def get_process_cache(*, default_ttl_sec: float | None = 60.0, max_entries: int = 2048) -> MemoryTTLCache[object]:
    return MemoryTTLCache(default_ttl_sec=default_ttl_sec, max_entries=max_entries)
