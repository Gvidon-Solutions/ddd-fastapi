"""Read agent run events from Redis streams."""

import json
from collections.abc import AsyncGenerator, Mapping
from typing import Any, cast

from faststream.redis.message import bDATA_KEY
from faststream.redis.parser import BinaryMessageFormatV1
from redis.asyncio import Redis

from app.config import settings

type AgentRunEventStreamMessage = dict[str, Any]


def decode_agent_run_event_fields(
    fields: Mapping[bytes, bytes],
) -> AgentRunEventStreamMessage:
    """Decode one FastStream Redis Stream field map."""
    raw_payload = fields.get(bDATA_KEY)
    if raw_payload is None:
        return {key.decode(): value.decode() for key, value in fields.items()}

    body, _headers = BinaryMessageFormatV1.parse(raw_payload)
    decoded = json.loads(body.decode())
    return cast(AgentRunEventStreamMessage, decoded)


async def iter_agent_run_events(
    run_id: str,
    last_event_id: str = "0-0",
) -> AsyncGenerator[tuple[str, AgentRunEventStreamMessage]]:
    """Yield persisted agent run events for a run from Redis Stream."""
    redis = Redis.from_url(settings.REDIS_URL)
    current_event_id = last_event_id
    try:
        while True:
            response = await redis.xread(
                {settings.AGENT_EVENTS_STREAM: current_event_id},
                count=20,
                block=15_000,
            )
            for _stream_name, stream_events in response:
                for message_id, fields in stream_events:
                    current_event_id = message_id.decode()
                    message = decode_agent_run_event_fields(fields)
                    if message.get("run_id") == run_id:
                        yield current_event_id, message
    finally:
        await redis.aclose()
