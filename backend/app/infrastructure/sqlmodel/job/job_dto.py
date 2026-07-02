"""Job SQLModel DTO."""

from __future__ import annotations

import uuid
from dataclasses import is_dataclass
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from app.domain.job import (
    Job,
    JobError,
    JobSerializationError,
    JobStatus,
    deserialize_json,
    job_registry,
    serialize_json,
)
from app.infrastructure.sqlmodel.datetime import ensure_datetime_utc, get_datetime_utc


class JobDTO(SQLModel, table=True):
    """Persisted job record."""

    __tablename__ = "job"

    job_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type: str = Field(min_length=1, max_length=255, index=True)
    version: str = Field(min_length=2, max_length=32, index=True)
    name: str | None = Field(default=None, max_length=255, index=True)
    description: str | None = Field(default=None)
    input: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    result: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    status: str = Field(max_length=32, index=True)
    initiator_id: uuid.UUID = Field(foreign_key="initiator.initiator_id", index=True)
    parent_job_id: uuid.UUID | None = Field(default=None, foreign_key="job.job_id")
    requested_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    started_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    error: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))

    def to_entity(self, initiator) -> Job:
        """Convert this persistence DTO to a typed domain entity."""
        contract = job_registry.get(type=self.type, version=self.version)
        try:
            input_obj = deserialize_json(self.input, contract.input)
            result_obj = None
            if self.result is not None:
                if JobStatus(self.status) == JobStatus.SUCCEEDED:
                    result_obj = deserialize_json(self.result, contract.result)
                else:
                    result_obj = self.result
        except JobSerializationError:
            raise
        except Exception as exc:
            raise JobSerializationError(str(exc)) from exc

        return Job(
            id=self.job_id,
            type=self.type,
            version=self.version,
            name=self.name,
            description=self.description,
            input=input_obj,
            result=result_obj,
            status=JobStatus(self.status),
            initiator=initiator,
            parent_job_id=self.parent_job_id,
            requested_at=ensure_datetime_utc(self.requested_at),
            updated_at=ensure_datetime_utc(self.updated_at),
            started_at=ensure_datetime_utc(self.started_at)
            if self.started_at is not None
            else None,
            finished_at=ensure_datetime_utc(self.finished_at)
            if self.finished_at is not None
            else None,
            error=_error_to_entity(self.error),
        )

    @staticmethod
    def from_entity(job: Job, *, initiator_id: uuid.UUID) -> JobDTO:
        """Build a persistence DTO from a domain entity."""
        return JobDTO(
            job_id=job.id,
            type=job.type,
            version=job.version,
            name=job.name,
            description=job.description,
            input=_to_record(job.input) or {},
            result=_to_record(job.result),
            status=job.status.value,
            initiator_id=initiator_id,
            parent_job_id=job.parent_job_id,
            requested_at=job.requested_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error=_error_to_record(job.error),
        )


def _to_record(value) -> dict | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if is_dataclass(value):
        serialized = serialize_json(value)
        if not isinstance(serialized, dict):
            raise JobSerializationError("Expected dataclass to serialize to object")
        return serialized
    return value


def _error_to_entity(error: dict | None) -> JobError | None:
    if error is None:
        return None
    return JobError(
        code=error["code"],
        message=error["message"],
        details=error.get("details") or {},
        retryable=bool(error.get("retryable", False)),
    )


def _error_to_record(error: JobError | None) -> dict | None:
    if error is None:
        return None
    return {
        "code": error.code,
        "message": error.message,
        "details": error.details,
        "retryable": error.retryable,
    }
