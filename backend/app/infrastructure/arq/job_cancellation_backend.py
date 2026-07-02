"""Redis-backed job cancellation backend."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from arq.connections import ArqRedis, create_pool

from app.infrastructure.arq.settings import arq_redis_settings
from app.usecase.job.ports import JobCancellationBackend


class RedisJobCancellationBackend(JobCancellationBackend):
    """Store running-job cancellation requests in Redis."""

    def __init__(self, redis: Any | None = None, *, ttl_seconds: int = 24 * 60 * 60):
        """Store Redis dependencies."""
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    async def request_cancel(self, job_id: UUID) -> None:
        """Request cancellation for a running job."""
        if self.redis is not None:
            await self.redis.set(_key(job_id), "1", ex=self.ttl_seconds)
            return
        async with self._redis_pool() as redis:
            await redis.set(_key(job_id), "1", ex=self.ttl_seconds)

    async def is_cancel_requested(self, job_id: UUID) -> bool:
        """Return whether cancellation was requested."""
        if self.redis is not None:
            return await self.redis.exists(_key(job_id)) > 0
        async with self._redis_pool() as redis:
            return await redis.exists(_key(job_id)) > 0

    async def clear_cancel_request(self, job_id: UUID) -> None:
        """Clear the cancellation request."""
        if self.redis is not None:
            await self.redis.delete(_key(job_id))
            return
        async with self._redis_pool() as redis:
            await redis.delete(_key(job_id))

    @asynccontextmanager
    async def _redis_pool(self) -> AsyncIterator[ArqRedis]:
        redis = await create_pool(arq_redis_settings())
        try:
            yield redis
        finally:
            await redis.aclose()


def _key(job_id: UUID) -> str:
    return f"job_cancel_requested:{job_id}"


def new_redis_job_cancellation_backend() -> JobCancellationBackend:
    """Create a Redis-backed cancellation backend."""
    return RedisJobCancellationBackend()
