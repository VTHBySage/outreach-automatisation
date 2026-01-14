"""Redis distributed lock for preventing race conditions in scheduled tasks."""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as redis

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisLock:
    """
    Distributed lock using Redis for preventing concurrent execution.

    Used to ensure scheduled tasks (like re-engagement processing) don't
    run simultaneously across multiple workers, which could cause:
    - Duplicate lead processing
    - Race conditions in database updates
    - Wasted API calls
    """

    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or settings.redis_url
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
            )
        return self._client

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def acquire(
        self,
        lock_name: str,
        timeout: int = 3600,
        blocking: bool = False,
        blocking_timeout: int = 10,
    ) -> bool:
        """
        Acquire a distributed lock.

        Args:
            lock_name: Unique identifier for the lock
            timeout: Lock expiration time in seconds (auto-release safety)
            blocking: If True, wait for the lock to become available
            blocking_timeout: Maximum time to wait if blocking

        Returns:
            True if lock acquired, False otherwise
        """
        client = await self._get_client()
        lock_key = f"lock:{lock_name}"

        if blocking:
            start_time = time.time()
            while time.time() - start_time < blocking_timeout:
                if await client.set(lock_key, "1", ex=timeout, nx=True):
                    logger.debug(
                        "lock_acquired",
                        lock_name=lock_name,
                        timeout=timeout,
                    )
                    return True
                await self._sleep(0.1)
            return False
        else:
            result = await client.set(lock_key, "1", ex=timeout, nx=True)
            if result:
                logger.debug(
                    "lock_acquired",
                    lock_name=lock_name,
                    timeout=timeout,
                )
            return bool(result)

    async def release(self, lock_name: str) -> bool:
        """
        Release a distributed lock.

        Args:
            lock_name: Unique identifier for the lock

        Returns:
            True if lock was released, False if it didn't exist
        """
        client = await self._get_client()
        lock_key = f"lock:{lock_name}"

        result = await client.delete(lock_key)
        if result:
            logger.debug(
                "lock_released",
                lock_name=lock_name,
            )
        return bool(result)

    async def is_locked(self, lock_name: str) -> bool:
        """Check if a lock is currently held."""
        client = await self._get_client()
        lock_key = f"lock:{lock_name}"
        return bool(await client.exists(lock_key))

    async def _sleep(self, seconds: float) -> None:
        """Async sleep helper."""
        import asyncio
        await asyncio.sleep(seconds)

    @asynccontextmanager
    async def lock(
        self,
        lock_name: str,
        timeout: int = 3600,
        blocking: bool = False,
        blocking_timeout: int = 10,
    ) -> AsyncGenerator[bool, None]:
        """
        Context manager for acquiring and releasing locks.

        Usage:
            async with redis_lock.lock("reengagement_processing") as acquired:
                if acquired:
                    # Do work
                else:
                    # Lock not acquired, skip
        """
        acquired = await self.acquire(
            lock_name=lock_name,
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
        )
        try:
            yield acquired
        finally:
            if acquired:
                await self.release(lock_name)


# Global instance for convenience
_redis_lock: RedisLock | None = None


def get_redis_lock() -> RedisLock:
    """Get global Redis lock instance."""
    global _redis_lock
    if _redis_lock is None:
        _redis_lock = RedisLock()
    return _redis_lock
