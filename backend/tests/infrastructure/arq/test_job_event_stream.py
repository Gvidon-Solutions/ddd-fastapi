"""Redis job event stream tests."""

from typing import Any, cast
from uuid import UUID

import msgspec
import pytest
from arq.connections import ArqRedis

from app.domain.job import JobId
from app.infrastructure.arq.job_event_stream import RedisJobEventStream

pytestmark = pytest.mark.anyio


class FakeRedis:
    """Return fixed Redis stream batches."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []
        self.returned = False

    async def xread(
        self,
        streams: dict[str, str],
        *,
        count: int,
        block: int,
    ) -> list:
        """Return one stream event once."""
        self.calls.append(streams)
        if self.returned:
            return []
        self.returned = True
        event = {
            "event_id": "22222222-2222-2222-2222-222222222222",
            "type": "CodexExecOutputV1",
            "source": "codex_exec",
            "version": "v1",
            "created_at": "2026-07-08T12:30:00Z",
            "payload": {
                "job_id": "11111111-1111-1111-1111-111111111111",
                "channel": "stdout",
                "line_number": 1,
                "line": "running",
            },
        }
        return [
            (
                b"job-events:11111111-1111-1111-1111-111111111111",
                [(b"1-0", {b"event": msgspec.json.encode(event)})],
            )
        ]


async def test_redis_job_event_stream_reads_decoded_events() -> None:
    # Arrange
    job_id = JobId(UUID("11111111-1111-1111-1111-111111111111"))
    redis = FakeRedis()
    stream = RedisJobEventStream(
        cast(ArqRedis, redis),
        stream_prefix="job-events",
        block_ms=5,
        count=1,
    )

    # Act
    messages = []
    async for message in stream.listen(job_id, last_event_id="0-0"):
        messages.append(message)
        break

    # Assert
    assert redis.calls == [{"job-events:11111111-1111-1111-1111-111111111111": "0-0"}]
    assert messages[0].stream_id == "1-0"
    assert messages[0].event["type"] == "CodexExecOutputV1"
    payload = cast(dict[str, Any], messages[0].event["payload"])
    assert payload["line"] == "running"
