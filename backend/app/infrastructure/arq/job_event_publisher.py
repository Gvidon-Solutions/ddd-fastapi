"""Redis implementation of the job event publisher port."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import msgspec
from arq.connections import ArqRedis, create_pool

from app.config import settings
from app.domain.job import JobEvent, JobId
from app.infrastructure.arq.settings import arq_redis_settings
from app.infrastructure.event import dump_event
from app.usecase.job.ports import EventPublisher

_encoder = msgspec.json.Encoder()


class RedisEventPublisher(EventPublisher):
    """Publish job events into per-job Redis streams."""

    def __init__(
        self,
        redis: ArqRedis,
        *,
        stream_prefix: str = settings.JOB_EVENTS_STREAM_PREFIX,
        maxlen: int = settings.JOB_EVENTS_STREAM_MAXLEN,
    ):
        """Store Redis event publisher dependencies."""
        self.redis = redis
        self.stream_prefix = stream_prefix
        self.maxlen = maxlen

    async def emit(self, job_id: JobId, event: JobEvent) -> None:
        """Publish one event to the stream owned by the job instance."""
        await self.redis.xadd(
            _stream_name(self.stream_prefix, job_id),
            fields={
                "event": _encoder.encode(dump_event(event)),
            },
            maxlen=self.maxlen,
            approximate=True,
        )


class RedisPoolEventPublisher(EventPublisher):
    """Open Redis connections for job event publishing."""

    def __init__(
        self,
        *,
        stream_prefix: str = settings.JOB_EVENTS_STREAM_PREFIX,
        maxlen: int = settings.JOB_EVENTS_STREAM_MAXLEN,
    ):
        """Store Redis event publisher configuration."""
        self.stream_prefix = stream_prefix
        self.maxlen = maxlen

    async def emit(self, job_id: JobId, event: JobEvent) -> None:
        """Publish one event with a short-lived Redis pool."""
        async with self._redis_pool() as redis:
            await self._publisher(redis).emit(job_id, event)

    def _publisher(self, redis: ArqRedis) -> RedisEventPublisher:
        """Create a Redis event publisher for one Redis connection."""
        return RedisEventPublisher(
            redis,
            stream_prefix=self.stream_prefix,
            maxlen=self.maxlen,
        )

    @asynccontextmanager
    async def _redis_pool(self) -> AsyncIterator[ArqRedis]:
        """Open and close an ARQ Redis pool."""
        redis = await create_pool(arq_redis_settings())
        try:
            yield redis
        finally:
            await redis.aclose()


def _stream_name(stream_prefix: str, job_id: JobId) -> str:
    return f"{stream_prefix}:{job_id}"


def new_redis_event_publisher(redis: ArqRedis) -> EventPublisher:
    """Create a Redis-backed event publisher from an existing Redis connection."""
    return RedisEventPublisher(redis)


def new_redis_pool_event_publisher() -> EventPublisher:
    """Create a Redis-backed event publisher that opens Redis connections."""
    return RedisPoolEventPublisher()
