"""Redis implementation of the job event stream port."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any, cast

import msgspec
from arq.connections import ArqRedis, create_pool

from app.config import settings
from app.domain.job import JobId
from app.infrastructure.arq.settings import arq_redis_settings
from app.usecase.job import JobEventStream, JobEventStreamMessage

_decoder = msgspec.json.Decoder()


class RedisJobEventStream(JobEventStream):
    """Read job events from per-job Redis streams."""

    def __init__(
        self,
        redis: ArqRedis,
        *,
        stream_prefix: str = settings.JOB_EVENTS_STREAM_PREFIX,
        block_ms: int = 1_000,
        count: int = 100,
    ):
        """Store Redis event stream dependencies."""
        self.redis = redis
        self.stream_prefix = stream_prefix
        self.block_ms = block_ms
        self.count = count

    async def listen(
        self,
        job_id: JobId,
        *,
        last_event_id: str = "0-0",
    ) -> AsyncIterator[JobEventStreamMessage]:
        """Yield decoded job event messages from Redis."""
        stream_name = _stream_name(self.stream_prefix, job_id)
        current_id = last_event_id
        while True:
            batches = await self.redis.xread(
                {stream_name: current_id},
                count=self.count,
                block=self.block_ms,
            )
            for _stream, entries in batches or []:
                for stream_id, fields in entries:
                    current_id = _to_text(stream_id)
                    yield JobEventStreamMessage(
                        stream_id=current_id,
                        event=_decode_event_field(fields),
                    )


class RedisPoolJobEventStream(JobEventStream):
    """Open Redis connections for job event stream reads."""

    def __init__(
        self,
        *,
        stream_prefix: str = settings.JOB_EVENTS_STREAM_PREFIX,
        block_ms: int = 1_000,
        count: int = 100,
    ):
        """Store Redis event stream configuration."""
        self.stream_prefix = stream_prefix
        self.block_ms = block_ms
        self.count = count

    async def listen(
        self,
        job_id: JobId,
        *,
        last_event_id: str = "0-0",
    ) -> AsyncIterator[JobEventStreamMessage]:
        """Yield decoded job event messages with a short-lived Redis pool."""
        async with self._redis_pool() as redis:
            stream = RedisJobEventStream(
                redis,
                stream_prefix=self.stream_prefix,
                block_ms=self.block_ms,
                count=self.count,
            )
            async for message in stream.listen(job_id, last_event_id=last_event_id):
                yield message

    @asynccontextmanager
    async def _redis_pool(self) -> AsyncIterator[ArqRedis]:
        """Open and close an ARQ Redis pool."""
        redis = await create_pool(arq_redis_settings())
        try:
            yield redis
        finally:
            await redis.aclose()


def _decode_event_field(fields: Mapping[object, object]) -> dict[str, object]:
    event = _field(fields, "event")
    decoded = _decoder.decode(event)
    if not isinstance(decoded, dict):
        raise ValueError("Job event stream message must contain an event object")
    return cast(dict[str, object], decoded)


def _field(fields: Mapping[object, object], name: str) -> bytes:
    value = fields.get(name)
    if value is None:
        value = fields.get(name.encode())
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode()
    raise ValueError(f"Missing Redis stream field `{name}`")


def _stream_name(stream_prefix: str, job_id: JobId) -> str:
    return f"{stream_prefix}:{job_id}"


def _to_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


def new_redis_job_event_stream(redis: ArqRedis) -> JobEventStream:
    """Create a Redis-backed job event stream from an existing connection."""
    return RedisJobEventStream(redis)


def new_redis_pool_job_event_stream() -> JobEventStream:
    """Create a Redis-backed job event stream that opens Redis connections."""
    return RedisPoolJobEventStream()
