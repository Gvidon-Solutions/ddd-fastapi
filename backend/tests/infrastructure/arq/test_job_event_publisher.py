"""Redis job event publisher tests."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import msgspec
import pytest
from arq.connections import ArqRedis

from app.domain.job import JobId
from app.domain.job.codex_run_job_use_case import (
    Event1CodexRunStarted,
    Event1CodexRunStartedPayload,
)
from app.infrastructure.arq.job_event_publisher import RedisEventPublisher

pytestmark = pytest.mark.anyio


class FakeRedis:
    """Record Redis stream writes."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    async def xadd(
        self,
        name: str,
        fields: dict[str, bytes],
        *,
        maxlen: int,
        approximate: bool,
    ) -> None:
        """Record one Redis stream entry."""
        self.entries.append(
            {
                "name": name,
                "fields": fields,
                "maxlen": maxlen,
                "approximate": approximate,
            }
        )


async def test_redis_event_publisher_emits_to_job_scoped_stream() -> None:
    # Arrange
    job_id = JobId(UUID("11111111-1111-1111-1111-111111111111"))
    redis = FakeRedis()
    publisher = RedisEventPublisher(
        cast(ArqRedis, redis),
        stream_prefix="job-events",
        maxlen=5,
    )
    event = Event1CodexRunStarted(
        created_at=datetime(2026, 7, 8, 12, 30, tzinfo=UTC),
        payload=Event1CodexRunStartedPayload(
            job_id=job_id,
            stage="codex_run",
            workdir="/tmp/work",
        ),
    )

    # Act
    await publisher.emit(job_id, event)

    # Assert
    entry = redis.entries[0]
    fields = entry["fields"]
    event = msgspec.json.decode(fields["event"])
    payload = event["payload"]
    assert entry["name"] == "job-events:11111111-1111-1111-1111-111111111111"
    assert entry["maxlen"] == 5
    assert entry["approximate"] is True
    assert isinstance(fields["event"], bytes)
    assert "job_id" not in event
    assert UUID(event["event_id"])
    assert event["type"] == "CodexRunStartedV1"
    assert event["source"] == "codex_run"
    assert event["version"] == "v1"
    assert event["created_at"] == "2026-07-08T12:30:00Z"
    assert payload["job_id"] == "11111111-1111-1111-1111-111111111111"
    assert payload["stage"] == "codex_run"
    assert payload["workdir"] == "/tmp/work"
