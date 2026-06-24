"""Event SQLModel DTO."""

from __future__ import annotations

import uuid
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from typing import TypeVar, get_type_hints

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from app.domain.event import Event, get_event_class
from app.domain.job import JobEvent, JobEventPayload, JobEventType
from app.infrastructure.sqlmodel.datetime import ensure_datetime_utc, get_datetime_utc

EventT = TypeVar("EventT", bound=Event)


class EventDTO(SQLModel, table=True):
    """Persisted event record."""

    __tablename__ = "event"

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type: str = Field(max_length=255, index=True)
    source: str = Field(max_length=255, index=True)
    version: str = Field(max_length=32)
    job_id_issuer: uuid.UUID | None = Field(
        default=None,
        foreign_key="job.job_id",
        index=True,
    )
    job_event_type: str | None = Field(default=None, max_length=64, index=True)
    message: str | None = Field(default=None)
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
        if self.job_id_issuer is None:
            raise ValueError("Job event requires job_id_issuer")
        if self.job_event_type is None:
            raise ValueError("Job event requires job_event_type")
        return JobEvent(
            event_id=self.event_id,
            type=self.type,
            source=self.source,
            version=self.version,
            created_at=ensure_datetime_utc(self.created_at or get_datetime_utc()),
            payload=JobEventPayload(
                job_id_issuer=self.job_id_issuer,
                job_event_type=JobEventType(self.job_event_type),
                message=self.message,
            ),
        )

    def _typed_payload(self, event_class: type[EventT]) -> JobEventPayload:
        payload_type = get_type_hints(event_class)["payload"]
        if not is_dataclass(payload_type):
            raise TypeError("Event payload type must be a dataclass")
        payload_kwargs = {
            "job_id_issuer": self._job_id_issuer(),
            "job_event_type": self._job_event_type(),
            "message": self.message,
            **self.payload,
        }
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

    def _job_id_issuer(self) -> uuid.UUID:
        if self.job_id_issuer is None:
            raise ValueError("Job event requires job_id_issuer")
        return self.job_id_issuer

    def _job_event_type(self) -> JobEventType:
        if self.job_event_type is None:
            raise ValueError("Job event requires job_event_type")
        return JobEventType(self.job_event_type)

    @staticmethod
    def from_job_event(event: JobEvent) -> EventDTO:
        """Build a persistence DTO from a job event domain entity."""
        return EventDTO(
            event_id=event.event_id,
            type=event.type,
            source=event.source,
            version=event.version,
            job_id_issuer=event.payload.job_id_issuer,
            job_event_type=event.payload.job_event_type.value,
            message=event.payload.message,
            payload=_payload_to_record(event.payload),
            created_at=event.created_at,
        )


def _data_to_record(data):
    if is_dataclass(data):
        return asdict(data)
    return data


def _payload_to_record(payload: JobEventPayload) -> dict:
    payload_record = _data_to_record(payload)
    return {
        key: value
        for key, value in payload_record.items()
        if key not in {"job_id_issuer", "job_event_type", "message"}
    }


def _coerce_value(value, target_type):
    if is_dataclass(target_type) and isinstance(value, dict):
        return target_type(**value)
    return value
