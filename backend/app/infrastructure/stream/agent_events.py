"""Publish agent run events through FastStream Redis streams."""

from app.config import settings
from app.domain.agent.entities import AgentRunEvent
from app.domain.agent.value_objects.agent_event_payload import PayloadValue
from app.infrastructure.stream.redis import redis_broker

type AgentRunEventMessage = dict[str, str | PayloadValue]


def agent_run_event_to_message(event: AgentRunEvent) -> AgentRunEventMessage:
    """Convert a domain event to a Redis-stream message payload."""
    return {
        "run_id": str(event.run_id.value),
        "event_type": event.event_type.value,
        "payload": event.payload.value,
        "created_at": event.created_at.isoformat(),
    }


async def publish_agent_run_event(event: AgentRunEvent) -> None:
    """Publish an agent run event to the configured Redis stream."""
    await redis_broker.connect()
    try:
        await redis_broker.publish(
            agent_run_event_to_message(event),
            stream=settings.AGENT_EVENTS_STREAM,
            maxlen=settings.AGENT_EVENTS_STREAM_MAXLEN,
        )
    finally:
        await redis_broker.stop()
