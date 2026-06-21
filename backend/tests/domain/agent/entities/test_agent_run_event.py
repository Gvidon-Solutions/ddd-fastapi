"""AgentRunEvent entity tests."""

from app.domain.agent.entities import AgentRunEvent
from app.domain.agent.value_objects import (
    AgentEventPayload,
    AgentEventType,
    AgentRunId,
)


def test_agent_run_event_create_stores_event_data() -> None:
    # Arrange
    run_id = AgentRunId.generate()
    event_type = AgentEventType.STARTED
    payload = AgentEventPayload({"message": "started"})

    # Act
    event = AgentRunEvent.create(run_id, event_type, payload)

    # Assert
    assert event.run_id == run_id
    assert event.event_type == event_type
    assert event.payload == payload
    assert event.created_at is not None
