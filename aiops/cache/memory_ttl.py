from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Callable, Dict, Generic, TypeVar

from .base import Cache, CacheStats, MISSING

T = TypeVar("T")


@dataclass(slots=True)
class _Entry(Generic[T]):
    value: T
    expires_at: float | None


class MemoryTTLCache(Cache[T]):
    def __init__(
        self,
        *,
        default_ttl_sec: float | None = 60.0,
        max_entries: int = 2048,
        now: Callable[[], float] = monotonic,
    ) -> None:
        self._default_ttl_sec = default_ttl_sec
        self._max_entries = max_entries
        self._now = now
        self._lock = Lock()
        self._store: Dict[str, _Entry[T]] = {}
        self._stats = CacheStats()

    def _is_expired(self, entry: _Entry[T], now: float) -> bool:
        if entry.expires_at is None:
            return False
        return now >= entry.expires_at

    def _purge_one_expired(self, now: float) -> bool:
        for key, entry in list(self._store.items()):
            if self._is_expired(entry, now):
                self._store.pop(key, None)
                self._stats.expired += 1
                return True
        return False

    def get(self, key: str, default: object = MISSING) -> T | object:
        now = self._now()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._stats.misses += 1
                return default
            if self._is_expired(entry, now):
                self._store.pop(key, None)
                self._stats.expired += 1
                self._stats.misses += 1
                return default
            self._stats.hits += 1
            return entry.value

    def set(self, key: str, value: T, *, ttl_sec: float | None = None) -> None:
        effective_ttl = self._default_ttl_sec if ttl_sec is None else ttl_sec
        now = self._now()
        expires_at = None if effective_ttl is None else (now + float(effective_ttl))
        with self._lock:
            self._stats.sets += 1
            self._store[key] = _Entry(value=value, expires_at=expires_at)
            while len(self._store) > self._max_entries:
                if self._purge_one_expired(now):
                    continue
                self._store.pop(next(iter(self._store)))
                self._stats.evicted += 1

    def delete(self, key: str) -> None:
        with self._lock:
            existed = key in self._store
            self._store.pop(key, None)
            if existed:
                self._stats.deletes += 1

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def stats(self) -> CacheStats:
        return CacheStats(
            hits=self._stats.hits,
            misses=self._stats.misses,
            sets=self._stats.sets,
            deletes=self._stats.deletes,
            expired=self._stats.expired,
            evicted=self._stats.evicted,
        )
