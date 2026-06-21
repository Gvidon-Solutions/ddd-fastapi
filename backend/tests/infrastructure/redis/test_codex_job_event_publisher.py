"""Redis Codex job event publisher tests."""

import pytest

from app.domain.codex_job.value_objects import CodexJobId
from app.infrastructure.redis import RedisCodexJobEventPublisher

pytestmark = pytest.mark.anyio


class FakeRedis:
    """Fake Redis client."""

    def __init__(self) -> None:
        """Initialize fake calls."""
        self.xadd_calls: list[dict[str, object]] = []
        self.closed = False

    async def xadd(
        self,
        name: str,
        fields: dict[str, str],
        maxlen: int,
        approximate: bool,
    ) -> None:
        """Record one stream append."""
        self.xadd_calls.append(
            {
                "name": name,
                "fields": fields,
                "maxlen": maxlen,
                "approximate": approximate,
            }
        )

    async def aclose(self) -> None:
        """Record client close."""
        self.closed = True


async def test_redis_codex_job_event_publisher_writes_stream_entry() -> None:
    # Arrange
    redis = FakeRedis()
    codex_job_id = CodexJobId.generate()
    publisher = RedisCodexJobEventPublisher(
        redis_client_factory=lambda: redis,
        stream_name="codex-events",
        stream_maxlen=100,
    )

    # Act
    await publisher.publish(
        codex_job_id=codex_job_id,
        event_type="raw_response_event",
        payload='{"type":"raw_response_event"}',
    )

    # Assert
    assert redis.xadd_calls == [
        {
            "name": "codex-events",
            "fields": {
                "codex_job_id": str(codex_job_id.value),
                "event_type": "raw_response_event",
                "payload": '{"type":"raw_response_event"}',
            },
            "maxlen": 100,
            "approximate": True,
        }
    ]
    assert redis.closed is True
