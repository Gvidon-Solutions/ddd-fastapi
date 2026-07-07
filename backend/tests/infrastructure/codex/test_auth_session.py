"""Codex auth session Redis repository tests."""

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest
from arq.connections import ArqRedis

from app.domain.job import JobId
from app.domain.job.codex_auth_job_use_case import CodexAuthSessionStatus
from app.infrastructure.codex import RedisCodexAuthSessionRepository

pytestmark = pytest.mark.anyio


class FakeRedis:
    """Store Redis values in memory."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def set(self, key: str, value: str, *, ex: int) -> None:
        """Store a value with TTL."""
        self.values[key] = value
        self.ttls[key] = ex

    async def get(self, key: str) -> str | None:
        """Return a value."""
        return self.values.get(key)


async def test_redis_codex_auth_session_repository_uses_required_redis() -> None:
    redis = FakeRedis()
    repository = RedisCodexAuthSessionRepository(
        cast(ArqRedis, redis),
        pending_ttl_seconds=600,
        terminal_ttl_seconds=60,
    )
    job_id = JobId(UUID("11111111-1111-1111-1111-111111111111"))
    expires_at = datetime.now(UTC) + timedelta(minutes=5)

    await repository.save_pending(
        job_id=job_id,
        verification_url="https://example.com/device",
        user_code="ABCD-EFGH",
        expires_at=expires_at,
    )
    pending = await repository.get(job_id)
    await repository.mark_authenticated(job_id)
    authenticated = await repository.get(job_id)

    assert pending is not None
    assert pending.job_id == job_id
    assert pending.status == CodexAuthSessionStatus.PENDING
    assert pending.user_code == "ABCD-EFGH"
    assert authenticated is not None
    assert authenticated.status == CodexAuthSessionStatus.AUTHENTICATED
    assert authenticated.user_code is None
    assert redis.ttls[f"codex_auth_session:{job_id}"] == 60
