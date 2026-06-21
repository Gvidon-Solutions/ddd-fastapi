"""Agent event stream publisher tests."""

import pytest

from app.domain.agent.entities import AgentRunEvent
from app.domain.agent.value_objects import (
    AgentEventPayload,
    AgentEventType,
    AgentRunId,
)
from app.infrastructure.stream import (
    agent_run_event_to_message,
    decode_agent_run_event_fields,
)

pytestmark = pytest.mark.anyio


def test_agent_run_event_to_message_serializes_event() -> None:
    # Arrange
    agent_run_id = AgentRunId.generate()
    event = AgentRunEvent.create(
        run_id=agent_run_id,
        event_type=AgentEventType.STEP,
        payload=AgentEventPayload({"message": "working", "step": 1}),
    )

    # Act
    message = agent_run_event_to_message(event)

    # Assert
    assert message == {
        "run_id": str(agent_run_id.value),
        "event_type": "step",
        "payload": {"message": "working", "step": 1},
        "created_at": event.created_at.isoformat(),
    }


async def test_decode_agent_run_event_fields_decodes_faststream_payload() -> None:
    # Arrange
    from faststream.redis.message import bDATA_KEY
    from faststream.redis.parser import BinaryMessageFormatV1

    message = {"run_id": "run-id", "event_type": "step", "payload": {"step": 1}}
    raw_payload = await BinaryMessageFormatV1.encode(
        message=message,
        reply_to=None,
        headers=None,
        correlation_id="correlation-id",
    )

    # Act
    decoded = decode_agent_run_event_fields({bDATA_KEY: raw_payload})

    # Assert
    assert decoded == message
