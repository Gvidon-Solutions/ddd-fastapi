"""Event SQLModel DTO."""

from __future__ import annotations

import uuid
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from typing import TypeVar, get_type_hints

from sqlalchemy import JSON, Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.domain.event import Event, get_event_class
from app.domain.job import JobEvent, JobEventPayload
from app.infrastructure.sqlmodel.datetime import ensure_datetime_utc, get_datetime_utc

EventT = TypeVar("EventT", bound=Event)


class EventDTO(SQLModel, table=True):
    """Persisted event record."""

    __tablename__ = "event"

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type: str = Field(max_length=255, index=True)
    source: str = Field(max_length=255, index=True)
    version: str = Field(max_length=32)
    payload: dict = Field(
        default_factory=dict,
        sa_column=Column("payload", JSON, nullable=False),
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    def to_entity(self, event_class: type[EventT] | None = None) -> JobEvent | EventT:
        """Convert this persistence DTO to a domain event entity."""
        event_class = event_class or get_event_class(self.type)
        if event_class is None or event_class is JobEvent:
            return self.to_job_event()

        created_at = ensure_datetime_utc(self.created_at or get_datetime_utc())
        payload = self._typed_payload(event_class)
        event = event_class(
            created_at=created_at,
            payload=payload,
        )
        event.event_id = self.event_id
        event.type = self.type
        event.source = self.source
        event.version = self.version
        return event

    def to_job_event(self) -> JobEvent:
        """Convert this persistence DTO to a base job event domain entity."""
        return JobEvent(
            event_id=self.event_id,
            type=self.type,
            source=self.source,
            version=self.version,
            created_at=ensure_datetime_utc(self.created_at or get_datetime_utc()),
            payload=JobEventPayload(),
        )

    def _typed_payload(self, event_class: type[EventT]) -> JobEventPayload:
        payload_type = get_type_hints(event_class)["payload"]
        if not is_dataclass(payload_type):
            raise TypeError("Event payload type must be a dataclass")
        payload_kwargs = self.payload
        type_hints = get_type_hints(payload_type)
        init_kwargs = {}
        for payload_field in fields(payload_type):
            if not payload_field.init or payload_field.name not in payload_kwargs:
                continue
            value = payload_kwargs[payload_field.name]
            init_kwargs[payload_field.name] = _coerce_value(
                value,
                type_hints.get(payload_field.name, payload_field.type),
            )
        return payload_type(**init_kwargs)

    @staticmethod
    def from_job_event(event: JobEvent) -> EventDTO:
        """Build a persistence DTO from a job event domain entity."""
        return EventDTO(
            event_id=event.event_id,
            type=event.type,
            source=event.source,
            version=event.version,
            payload=_payload_to_record(event.payload),
            created_at=event.created_at,
        )


def _data_to_record(data):
    if is_dataclass(data):
        return asdict(data)
    return data


def _payload_to_record(payload: JobEventPayload) -> dict:
    return _data_to_record(payload)


def _coerce_value(value, target_type):
    if is_dataclass(target_type) and isinstance(value, dict):
        return target_type(**value)
    return value


class JobEventLinkDTO(SQLModel, table=True):
    """Link an event to the job timeline that emitted it."""

    __tablename__ = "job_event"
    __table_args__ = (
        UniqueConstraint("job_id", "event_id", "relation"),
        UniqueConstraint("job_id", "sequence"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="job.job_id", index=True)
    event_id: uuid.UUID = Field(foreign_key="event.event_id", index=True)
    relation: str = Field(default="emitted", max_length=64)
    sequence: int = Field(index=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
