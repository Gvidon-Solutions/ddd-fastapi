"""JobEvent SQLModel DTO."""

from __future__ import annotations

import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from app.domain.job import JobEvent, JobEventType
from app.infrastructure.sqlmodel.datetime import ensure_datetime_utc, get_datetime_utc


class JobEventDTO(SQLModel, table=True):
    """Persisted job event record."""

    __tablename__ = "job_event"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="job.id", nullable=False, index=True)
    type: str = Field(max_length=64, index=True)
    data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    message: str | None = Field(default=None)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    def to_entity(self) -> JobEvent:
        """Convert this persistence DTO to a domain entity."""
        return JobEvent(
            id=self.id,
            job_id=self.job_id,
            type=JobEventType(self.type),
            data=self.data,
            message=self.message,
            created_at=ensure_datetime_utc(self.created_at or get_datetime_utc()),
        )

    @staticmethod
    def from_entity(event: JobEvent) -> JobEventDTO:
        """Build a persistence DTO from a domain entity."""
        return JobEventDTO(
            id=event.id,
            job_id=event.job_id,
            type=event.type.value,
            data=_data_to_record(event.data),
            message=event.message,
            created_at=event.created_at,
        )


def _data_to_record(data):
    if is_dataclass(data):
        return asdict(data)
    return data
