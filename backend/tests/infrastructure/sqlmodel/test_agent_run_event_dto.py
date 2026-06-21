"""AgentRunEventDTO tests."""

from app.domain.agent.entities import AgentRunEvent
from app.domain.agent.value_objects import (
    AgentEventPayload,
    AgentEventType,
    AgentRunId,
)
from app.infrastructure.sqlmodel.agent import AgentRunEventDTO


def test_agent_run_event_dto_uses_agent_run_event_table_name() -> None:
    # Act
    table_name = AgentRunEventDTO.__tablename__

    # Assert
    assert table_name == "agent_run_event"


def test_agent_run_event_dto_round_trips_event_fields() -> None:
    # Arrange
    event = AgentRunEvent.create(
        AgentRunId.generate(),
        AgentEventType.STEP,
        AgentEventPayload({"message": "working"}),
    )

    # Act
    entity = AgentRunEventDTO.from_entity(event).to_entity()

    # Assert
    assert entity.run_id == event.run_id
    assert entity.event_type == event.event_type
    assert entity.payload == event.payload
