"""Redis-based cache implementation for distributed caching.

This module provides a Redis backend for the cache system, enabling
distributed caching across multiple AIOps instances.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Generic, TypeVar

from aiops.cache.base import Cache, CacheStats, MISSING

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RedisCache(Cache[T]):
    """Redis-based cache implementation.

    This cache uses Redis as a backend, allowing for distributed caching
    and persistence across restarts.

    Example:
        ```python
        cache = RedisCache(
            redis_url="redis://localhost:6379/0",
            key_prefix="aiops:",
            default_ttl_sec=300
        )

        # Set a value
        await cache.set("user:123", {"name": "Alice"})

        # Get a value
        user = await cache.get("user:123")

        # Get or set with factory
        result = await cache.get_or_set(
            "expensive_query",
            lambda: run_expensive_query(),
            ttl_sec=600
        )
        ```

    Args:
        redis_url: Redis connection URL (default: from env var REDIS_URL)
        key_prefix: Prefix for all keys in this cache (default: "aiops:")
        default_ttl_sec: Default TTL in seconds (default: 60)
        pool_size: Connection pool size (default: 10)
    """

    def __init__(
        self,
        *,
        redis_url: str | None = None,
        key_prefix: str = "aiops:",
        default_ttl_sec: float | None = 60.0,
        pool_size: int = 10,
    ) -> None:
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._default_ttl_sec = default_ttl_sec
        self._pool_size = pool_size
        self._pool: Any = None  # redis.asyncio.ConnectionPool
        self._redis: Any = None  # redis.asyncio.Redis
        self._stats = CacheStats()
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Lazy initialization of Redis connection."""
        if self._initialized:
            return

        try:
            import redis.asyncio as aioredis
        except ImportError:
            raise ImportError(
                "redis package is required for RedisCache. "
                "Install it with: pip install redis"
            )

        url = self._redis_url or "redis://localhost:6379/0"
        self._pool = aioredis.ConnectionPool.from_url(
            url,
            max_connections=self._pool_size,
            decode_responses=True,
        )
        self._redis = aioredis.Redis(connection_pool=self._pool)
        self._initialized = True
        logger.info("redis_cache_initialized", url=url)

    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self._key_prefix}{key}"

    async def get(self, key: str, default: object = MISSING) -> T | object:
        """Get a value from the cache."""
        await self._ensure_initialized()

        redis_key = self._make_key(key)
        try:
            value = await self._redis.get(redis_key)
            if value is None:
                self._stats.misses += 1
                return default

            # Deserialize
            self._stats.hits += 1
            return json.loads(value)
        except Exception as e:
            logger.warning("redis_get_error", key=key, error=str(e))
            self._stats.misses += 1
            return default

    async def set(
        self,
        key: str,
        value: T,
        *,
        ttl_sec: float | None = None
    ) -> None:
        """Set a value in the cache."""
        await self._ensure_initialized()

        redis_key = self._make_key(key)
        effective_ttl = self._default_ttl_sec if ttl_sec is None else ttl_sec

        try:
            serialized = json.dumps(value)
            if effective_ttl is None:
                await self._redis.set(redis_key, serialized)
            else:
                await self._redis.setex(redis_key, int(effective_ttl), serialized)
            self._stats.sets += 1
        except Exception as e:
            logger.warning("redis_set_error", key=key, error=str(e))

    async def delete(self, key: str) -> None:
        """Delete a value from the cache."""
        await self._ensure_initialized()

        redis_key = self._make_key(key)
        try:
            existed = await self._redis.exists(redis_key)
            await self._redis.delete(redis_key)
            if existed:
                self._stats.deletes += 1
        except Exception as e:
            logger.warning("redis_delete_error", key=key, error=str(e))

    async def clear(self) -> None:
        """Clear all values from this cache (with prefix)."""
        await self._ensure_initialized()

        try:
            pattern = f"{self._key_prefix}*"
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self._redis.delete(*keys)
                logger.info("redis_cache_cleared", count=len(keys))
        except Exception as e:
            logger.warning("redis_clear_error", error=str(e))

    async def stats(self) -> CacheStats:
        """Get cache statistics."""
        # Get Redis info for additional stats
        await self._ensure_initialized()

        try:
            info = await self._redis.info("stats")
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                sets=self._stats.sets,
                deletes=self._stats.deletes,
                expired=self._stats.expired,
                evicted=self._stats.evicted,
            )
        except Exception:
            return self._stats

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._pool is not None:
            await self._pool.close()
            self._initialized = False
            logger.info("redis_cache_closed")

    async def __aenter__(self) -> RedisCache[T]:
        """Async context manager entry."""
        await self._ensure_initialized()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()


class RedisCacheFactory:
    """Factory for creating Redis cache instances."""

    _instances: dict[str, RedisCache[Any]] = {}

    @classmethod
    async def get_cache(
        cls,
        name: str = "default",
        **kwargs
    ) -> RedisCache[Any]:
        """Get or create a named Redis cache instance.

        Args:
            name: Name of the cache instance
            **kwargs: Arguments to pass to RedisCache

        Returns:
            A Redis cache instance
        """
        if name not in cls._instances:
            cls._instances[name] = RedisCache(**kwargs)
            await cls._instances[name]._ensure_initialized()

        return cls._instances[name]

    @classmethod
    async def close_all(cls) -> None:
        """Close all cache instances."""
        for cache in cls._instances.values():
            await cache.close()
        cls._instances.clear()


async def get_redis_cache(
    redis_url: str | None = None,
    key_prefix: str = "aiops:",
    default_ttl_sec: float | None = 60.0,
) -> RedisCache[Any]:
    """Get a Redis cache instance with default settings.

    Args:
        redis_url: Redis connection URL
        key_prefix: Key prefix for this cache
        default_ttl_sec: Default TTL in seconds

    Returns:
        A Redis cache instance
    """
    return await RedisCacheFactory.get_cache(
        "default",
        redis_url=redis_url,
        key_prefix=key_prefix,
        default_ttl_sec=default_ttl_sec,
    )
