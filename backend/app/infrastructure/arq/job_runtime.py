"""ARQ implementation of the job runtime port."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from arq.connections import ArqRedis, create_pool
from arq.jobs import Job

from app.config import settings
from app.domain.job import JobId
from app.infrastructure.arq.settings import arq_redis_settings
from app.usecase.job.ports import JobRuntime


class ArqJobRuntime(JobRuntime):
    """Run jobs through ARQ and store runtime cancellation markers in Redis."""

    def __init__(
        self,
        redis: ArqRedis,
        *,
        queue_name: str = settings.ARQ_QUEUE_NAME,
        cancel_ttl_seconds: int = 24 * 60 * 60,
    ):
        """Store ARQ Redis dependencies."""
        self.redis = redis
        self.queue_name = queue_name
        self.cancel_ttl_seconds = cancel_ttl_seconds

    async def enqueue(
        self,
        job_type: str,
        job_id: JobId,
    ) -> None:
        """Enqueue a persisted job by type and ID."""
        queued_job = await self.redis.enqueue_job(
            job_type,
            str(job_id),
            _queue_name=self.queue_name,
            _job_id=str(job_id),
        )
        if queued_job is None:
            raise RuntimeError(f"Job was not enqueued: {job_type}")

    async def cancel(self, job_id: JobId) -> bool:
        """Abort an enqueued or running ARQ job."""
        return await Job(
            str(job_id),
            self.redis,
            _queue_name=self.queue_name,
        ).abort()

    async def request_cancel(self, job_id: JobId) -> None:
        """Request cooperative cancellation for a running job."""
        await self.redis.set(
            _cancel_key(job_id),
            "1",
            ex=self.cancel_ttl_seconds,
        )

    async def is_cancel_requested(self, job_id: JobId) -> bool:
        """Return whether cooperative cancellation was requested."""
        return await self.redis.exists(_cancel_key(job_id)) > 0

    async def clear_cancel_request(self, job_id: JobId) -> None:
        """Clear the cooperative cancellation request."""
        await self.redis.delete(_cancel_key(job_id))

    async def await_terminal(
        self,
        job_id: JobId,
        *,
        timeout_seconds: float | None = None,
        poll_delay_seconds: float = 0.5,
    ) -> object:
        """Wait until ARQ stores the job result or raises its terminal error."""
        return await Job(
            str(job_id),
            self.redis,
            _queue_name=self.queue_name,
        ).result(
            timeout=timeout_seconds,
            poll_delay=poll_delay_seconds,
        )


class ArqPoolJobRuntime(JobRuntime):
    """Open ARQ Redis connections for runtime operations."""

    def __init__(
        self,
        *,
        queue_name: str = settings.ARQ_QUEUE_NAME,
        cancel_ttl_seconds: int = 24 * 60 * 60,
    ):
        """Store runtime configuration."""
        self.queue_name = queue_name
        self.cancel_ttl_seconds = cancel_ttl_seconds

    async def enqueue(
        self,
        job_type: str,
        job_id: JobId,
    ) -> None:
        """Enqueue a persisted job by type and ID."""
        async with self._redis_pool() as redis:
            await self._runtime(redis).enqueue(job_type=job_type, job_id=job_id)

    async def cancel(self, job_id: JobId) -> bool:
        """Abort an enqueued or running ARQ job."""
        async with self._redis_pool() as redis:
            return await self._runtime(redis).cancel(job_id)

    async def request_cancel(self, job_id: JobId) -> None:
        """Request cooperative cancellation for a running job."""
        async with self._redis_pool() as redis:
            await self._runtime(redis).request_cancel(job_id)

    async def is_cancel_requested(self, job_id: JobId) -> bool:
        """Return whether cooperative cancellation was requested."""
        async with self._redis_pool() as redis:
            return await self._runtime(redis).is_cancel_requested(job_id)

    async def clear_cancel_request(self, job_id: JobId) -> None:
        """Clear the cooperative cancellation request."""
        async with self._redis_pool() as redis:
            await self._runtime(redis).clear_cancel_request(job_id)

    async def await_terminal(
        self,
        job_id: JobId,
        *,
        timeout_seconds: float | None = None,
        poll_delay_seconds: float = 0.5,
    ) -> object:
        """Wait until ARQ stores the job result or raises its terminal error."""
        async with self._redis_pool() as redis:
            return await self._runtime(redis).await_terminal(
                job_id,
                timeout_seconds=timeout_seconds,
                poll_delay_seconds=poll_delay_seconds,
            )

    def _runtime(self, redis: ArqRedis) -> ArqJobRuntime:
        return ArqJobRuntime(
            redis,
            queue_name=self.queue_name,
            cancel_ttl_seconds=self.cancel_ttl_seconds,
        )

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


def _cancel_key(job_id: JobId) -> str:
    return f"job_cancel_requested:{job_id}"


def new_arq_job_runtime() -> JobRuntime:
    """Create an ARQ-backed job runtime."""
    return ArqPoolJobRuntime()
