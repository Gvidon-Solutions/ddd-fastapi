"""ARQ job runtime cancellation tests."""

from typing import cast
from uuid import UUID

import pytest
from arq.connections import ArqRedis

from app.domain.job import JobId
from app.infrastructure.arq import ArqJobRuntime

pytestmark = pytest.mark.anyio


class FakeRedis:
    """Record Redis cancellation operations."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.set_calls: list[tuple[str, str, int]] = []
        self.deleted: list[str] = []

    async def set(self, key: str, value: str, *, ex: int) -> None:
        """Store a value with TTL."""
        self.values[key] = value
        self.set_calls.append((key, value, ex))

    async def exists(self, key: str) -> int:
        """Return whether the key exists."""
        return int(key in self.values)

    async def delete(self, key: str) -> None:
        """Delete a key."""
        self.values.pop(key, None)
        self.deleted.append(key)


async def test_arq_job_runtime_uses_required_redis_for_cancel_markers() -> None:
    redis = FakeRedis()
    runtime = ArqJobRuntime(
        cast(ArqRedis, redis),
        cancel_ttl_seconds=60,
    )
    job_uuid = UUID("11111111-1111-1111-1111-111111111111")
    job_id = JobId(job_uuid)
    key = f"job_cancel_requested:{job_id}"

    await runtime.request_cancel(job_id)
    requested = await runtime.is_cancel_requested(job_id)
    await runtime.clear_cancel_request(job_id)

    assert requested is True
    assert redis.set_calls == [(key, "1", 60)]
    assert redis.deleted == [key]
    assert await runtime.is_cancel_requested(job_id) is False
