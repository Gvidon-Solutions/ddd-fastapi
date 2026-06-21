"""Redis publisher for Codex job streaming events."""

from collections.abc import Callable
from typing import Any

from redis.asyncio import Redis

from app.config import settings
from app.domain.codex_job.value_objects import CodexJobId
from app.usecase.codex_job import CodexJobEventPublisher

RedisClientFactory = Callable[[], Any]


class RedisCodexJobEventPublisher(CodexJobEventPublisher):
    """Publish Codex job events to a Redis Stream."""

    def __init__(
        self,
        redis_client_factory: RedisClientFactory | None = None,
        stream_name: str = settings.CODEX_JOB_EVENTS_STREAM,
        stream_maxlen: int = settings.CODEX_JOB_EVENTS_STREAM_MAXLEN,
    ):
        """Store Redis publishing settings."""
        self.redis_client_factory = redis_client_factory or self._new_redis_client
        self.stream_name = stream_name
        self.stream_maxlen = stream_maxlen

    async def publish(
        self,
        codex_job_id: CodexJobId,
        event_type: str,
        payload: str,
    ) -> None:
        """Publish one event to Redis."""
        redis = self.redis_client_factory()
        try:
            await redis.xadd(
                self.stream_name,
                {
                    "codex_job_id": str(codex_job_id.value),
                    "event_type": event_type,
                    "payload": payload,
                },
                maxlen=self.stream_maxlen,
                approximate=True,
            )
        finally:
            await redis.aclose()

    def _new_redis_client(self) -> Redis:
        """Create a Redis client."""
        return Redis.from_url(settings.REDIS_URL, decode_responses=True)


def new_codex_job_event_publisher() -> CodexJobEventPublisher:
    """Create a Codex job event publisher."""
    return RedisCodexJobEventPublisher()
