"""Event SQLModel DTO."""

from __future__ import annotations

import uuid
from dataclasses import is_dataclass
from datetime import datetime
from typing import Any, cast, get_type_hints
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import JSON, Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.domain.event import get_event_class
from app.domain.job import JobEvent, JobEventPayload
from app.infrastructure.sqlmodel.datetime import ensure_datetime_utc, get_datetime_utc


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

    def to_entity(
        self,
        event_class: Any | None = None,
        *,
        job_id: UUID | None = None,
    ) -> JobEvent:
        """Convert this persistence DTO to a domain event entity."""
        event_class = event_class or get_event_class(self.type)
        if event_class is None or event_class is JobEvent:
            return self.to_job_event(job_id=job_id)

        created_at = ensure_datetime_utc(self.created_at or get_datetime_utc())
        try:
            payload = self._typed_payload(event_class, job_id=job_id)
            event_factory: Any = event_class
            event = event_factory(
                created_at=created_at,
                payload=payload,
            )
        except Exception:
            return self.to_job_event(job_id=job_id)
        event.event_id = self.event_id
        event.type = self.type
        event.source = self.source
        event.version = self.version
        return cast(JobEvent, event)

    def to_job_event(self, *, job_id: UUID | None = None) -> JobEvent:
        """Convert this persistence DTO to a base job event domain entity."""
        return JobEvent(
            event_id=self.event_id,
            type=self.type,
            source=self.source,
            version=self.version,
            created_at=ensure_datetime_utc(self.created_at or get_datetime_utc()),
            payload=_base_payload_or_record(self.payload, job_id),
        )

    def _typed_payload(
        self,
        event_class: Any,
        *,
        job_id: UUID | None,
    ) -> JobEventPayload:
        from app.infrastructure.sqlmodel.job.payload_codec import load_payload

        payload_type = get_type_hints(event_class)["payload"]
        if not is_dataclass(payload_type):
            raise TypeError("Event payload type must be a dataclass")
        return load_payload(_payload_with_job_id(self.payload, job_id), payload_type)

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
        from app.infrastructure.sqlmodel.job.payload_codec import dump_payload

        return dump_payload(data)
    if isinstance(data, dict):
        return TypeAdapter(dict).dump_python(data, mode="json")
    return data


def _payload_to_record(payload: JobEventPayload | dict) -> dict:
    return _data_to_record(payload)


def _payload_with_job_id(payload: dict, job_id: UUID | None) -> dict:
    payload_with_job_id = dict(payload)
    if "job_id" not in payload_with_job_id and job_id is not None:
        payload_with_job_id["job_id"] = job_id
    return payload_with_job_id


def _base_payload_or_record(
    payload: dict,
    job_id: UUID | None,
) -> JobEventPayload | dict:
    payload_with_job_id = _payload_with_job_id(payload, job_id)
    if set(payload_with_job_id) == {"job_id"}:
        return JobEventPayload(job_id=UUID(str(payload_with_job_id["job_id"])))
    return payload_with_job_id


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
