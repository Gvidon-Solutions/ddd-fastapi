"""ARQ implementation of the job queue port."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from arq.connections import ArqRedis, create_pool

from app.config import settings
from app.infrastructure.arq.settings import arq_redis_settings
from app.usecase.job import JobQueue


class ArqJobQueue(JobQueue):
    """Enqueue generic jobs through ARQ."""

    def __init__(
        self,
        redis: Any | None = None,
        queue_name: str = settings.ARQ_QUEUE_NAME,
    ):
        """Store queue dependencies."""
        self.redis = redis
        self.queue_name = queue_name

    async def enqueue(
        self,
        job_name: str,
        job_id: UUID,
    ) -> None:
        """Enqueue a persisted job by name and ID."""
        if self.redis is not None:
            await self._enqueue(self.redis, job_name, job_id)
            return

        async with self._redis_pool() as redis:
            await self._enqueue(redis, job_name, job_id)

    async def _enqueue(
        self,
        redis: Any,
        job_name: str,
        job_id: UUID,
    ) -> None:
        """Enqueue a job using an existing Redis connection."""
        queued_job = await redis.enqueue_job(
            job_name,
            str(job_id),
            _queue_name=self.queue_name,
        )
        if queued_job is None:
            raise RuntimeError(f"Job was not enqueued: {job_name}")

    @asynccontextmanager
    async def _redis_pool(self) -> AsyncIterator[ArqRedis]:
        """Open and close an ARQ Redis pool."""
        redis = await create_pool(
            arq_redis_settings(),
            default_queue_name=self.queue_name,
        )
        try:
            yield redis
        finally:
            await redis.aclose()


def new_arq_job_queue() -> JobQueue:
    """Create an ARQ-backed job queue."""
    return ArqJobQueue()
