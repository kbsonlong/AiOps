from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar, overload, cast

T = TypeVar("T")

MISSING = object()


@dataclass(slots=True)
class CacheStats:
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    expired: int = 0
    evicted: int = 0


class Cache(ABC, Generic[T]):
    @overload
    def get(self, key: str) -> T | object: ...

    @overload
    def get(self, key: str, default: T) -> T: ...

    @abstractmethod
    def get(self, key: str, default: object = MISSING) -> T | object: ...

    @abstractmethod
    def set(self, key: str, value: T, *, ttl_sec: float | None = None) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def stats(self) -> CacheStats: ...

    def get_or_set(self, key: str, factory: Callable[[], T], *, ttl_sec: float | None = None) -> T:
        existing = self.get(key, MISSING)
        if existing is not MISSING:
            return cast(T, existing)
        created = factory()
        self.set(key, created, ttl_sec=ttl_sec)
        return created
