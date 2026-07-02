"""Job dispatch outbox SQLModel DTO."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from app.domain.job.base.entities import JobDispatchOutbox, JobDispatchOutboxStatus
from app.infrastructure.sqlmodel.datetime import ensure_datetime_utc, get_datetime_utc


class JobDispatchOutboxDTO(SQLModel, table=True):
    """Persisted durable job dispatch intent."""

    __tablename__ = "job_dispatch_outbox"

    outbox_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="job.job_id", index=True)
    type: str = Field(min_length=1, max_length=255, index=True)
    version: str = Field(min_length=2, max_length=32)
    status: str = Field(max_length=32, index=True)
    attempts: int = Field(default=0)
    next_attempt_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_error: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    dispatched_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    def to_entity(self) -> JobDispatchOutbox:
        """Convert this DTO to a domain outbox entry."""
        return JobDispatchOutbox(
            outbox_id=self.outbox_id,
            job_id=self.job_id,
            type=self.type,
            version=self.version,
            status=JobDispatchOutboxStatus(self.status),
            attempts=self.attempts,
            next_attempt_at=ensure_datetime_utc(self.next_attempt_at),
            last_error=self.last_error,
            created_at=ensure_datetime_utc(self.created_at),
            updated_at=ensure_datetime_utc(self.updated_at),
            dispatched_at=ensure_datetime_utc(self.dispatched_at)
            if self.dispatched_at is not None
            else None,
        )

    @staticmethod
    def from_entity(outbox: JobDispatchOutbox) -> JobDispatchOutboxDTO:
        """Build a DTO from a domain outbox entry."""
        return JobDispatchOutboxDTO(
            outbox_id=outbox.outbox_id,
            job_id=outbox.job_id,
            type=outbox.type,
            version=outbox.version,
            status=outbox.status.value,
            attempts=outbox.attempts,
            next_attempt_at=outbox.next_attempt_at,
            last_error=outbox.last_error,
            created_at=outbox.created_at,
            updated_at=outbox.updated_at,
            dispatched_at=outbox.dispatched_at,
        )
