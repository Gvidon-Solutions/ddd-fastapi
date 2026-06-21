"""AgentRunEvent SQLModel DTO."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from app.domain.agent.entities import AgentRunEvent
from app.domain.agent.value_objects import (
    AgentEventPayload,
    AgentEventType,
    AgentRunId,
)
from app.infrastructure.sqlmodel.datetime import get_datetime_utc


class AgentRunEventDTO(SQLModel, table=True):
    """Persisted agent run event record."""

    __tablename__ = "agent_run_event"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    run_id: uuid.UUID = Field(
        foreign_key="agent_run.id",
        nullable=False,
        ondelete="CASCADE",
        index=True,
    )
    event_type: str = Field(max_length=32, index=True)
    payload: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    def to_entity(self) -> AgentRunEvent:
        """Convert this persistence DTO to a domain entity."""
        return AgentRunEvent(
            run_id=AgentRunId(self.run_id),
            event_type=AgentEventType(self.event_type),
            payload=AgentEventPayload(self.payload),
            created_at=self.created_at or get_datetime_utc(),
        )

    @staticmethod
    def from_entity(event: AgentRunEvent) -> "AgentRunEventDTO":
        """Build a persistence DTO from a domain entity."""
        return AgentRunEventDTO(
            run_id=event.run_id.value,
            event_type=event.event_type.value,
            payload=event.payload.value,
            created_at=event.created_at,
        )
