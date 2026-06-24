"""Job SQLModel DTO."""

from __future__ import annotations

import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from app.domain.job import Actor, ActorType, Job, JobError, JobStage, JobStatus
from app.infrastructure.sqlmodel.datetime import ensure_datetime_utc, get_datetime_utc


class JobDTO(SQLModel, table=True):
    """Persisted job record."""

    __tablename__ = "job"

    job_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_type: str = Field(min_length=1, max_length=255, index=True)
    job_name: str = Field(min_length=1, max_length=255, index=True)
    job_description: str | None = Field(default=None)
    job_input: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    job_status: str = Field(max_length=32, index=True)
    job_stage: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    result_summary: dict | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    root_initiator: dict = Field(sa_column=Column(JSON, nullable=False))
    parent_job_id: uuid.UUID | None = Field(default=None, foreign_key="job.job_id")
    requested_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    started_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    job_error: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))

    def to_entity(self) -> Job:
        """Convert this persistence DTO to a domain entity."""
        return Job(
            job_id=self.job_id,
            job_type=self.job_type,
            job_name=self.job_name,
            job_description=self.job_description,
            job_input=self.job_input,
            job_status=JobStatus(self.job_status),
            job_stage=_stage_to_entity(self.job_stage),
            result_summary=self.result_summary,
            root_initiator=_actor_to_entity(self.root_initiator),
            parent_job_id=self.parent_job_id,
            requested_at=ensure_datetime_utc(self.requested_at or get_datetime_utc()),
            updated_at=ensure_datetime_utc(self.updated_at or get_datetime_utc()),
            started_at=ensure_datetime_utc(self.started_at)
            if self.started_at is not None
            else None,
            finished_at=ensure_datetime_utc(self.finished_at)
            if self.finished_at is not None
            else None,
            job_error=_error_to_entity(self.job_error),
        )

    @staticmethod
    def from_entity(job: Job) -> JobDTO:
        """Build a persistence DTO from a domain entity."""
        return JobDTO(
            job_id=job.job_id,
            job_type=job.job_type,
            job_name=job.job_name,
            job_description=job.job_description,
            job_input=job.job_input,
            job_status=job.job_status.value,
            job_stage=_stage_to_record(job.job_stage),
            result_summary=job.result_summary,
            root_initiator=_actor_to_record(job.root_initiator),
            parent_job_id=job.parent_job_id,
            requested_at=job.requested_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            job_error=_error_to_record(job.job_error),
        )


def _stage_to_entity(stage: dict | None) -> JobStage | None:
    if stage is None:
        return None
    return JobStage(
        key=stage["key"],
        current=stage.get("current"),
        total=stage.get("total"),
        message=stage.get("message"),
        updated_at=_datetime_to_entity(stage.get("updated_at")),
        data=stage.get("data"),
    )


def _stage_to_record(stage: JobStage | None) -> dict | None:
    if stage is None:
        return None
    return {
        "key": stage.key,
        "current": stage.current,
        "total": stage.total,
        "message": stage.message,
        "updated_at": stage.updated_at.isoformat()
        if stage.updated_at is not None
        else None,
        "data": _data_to_record(stage.data),
    }


def _datetime_to_entity(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_datetime_utc(value)
    if isinstance(value, str):
        return ensure_datetime_utc(datetime.fromisoformat(value))
    raise TypeError(f"Unsupported datetime value: {value!r}")


def _data_to_record(data):
    if data is None:
        return None
    if is_dataclass(data):
        return asdict(data)
    return data


def _actor_to_entity(actor: dict) -> Actor:
    return Actor(
        type=ActorType(actor["type"]),
        id=actor.get("id"),
        display_name=actor.get("display_name"),
    )


def _actor_to_record(actor: Actor) -> dict:
    return {
        "type": actor.type.value,
        "id": actor.id,
        "display_name": actor.display_name,
    }


def _error_to_entity(error: dict | None) -> JobError | None:
    if error is None:
        return None
    return JobError(
        code=error["code"],
        message=error["message"],
        details=error.get("details"),
    )


def _error_to_record(error: JobError | None) -> dict | None:
    if error is None:
        return None
    return {
        "code": error.code,
        "message": error.message,
        "details": error.details,
    }
