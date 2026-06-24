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

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(min_length=1, max_length=255, index=True)
    input: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    status: str = Field(max_length=32, index=True)
    stage: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    result_summary: dict | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    root_initiator: dict = Field(sa_column=Column(JSON, nullable=False))
    parent_job_id: uuid.UUID | None = Field(default=None, foreign_key="job.id")
    requested_at: datetime | None = Field(
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
    error: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))

    def to_entity(self) -> Job:
        """Convert this persistence DTO to a domain entity."""
        return Job(
            id=self.id,
            name=self.name,
            input=self.input,
            status=JobStatus(self.status),
            stage=_stage_to_entity(self.stage),
            result_summary=self.result_summary,
            root_initiator=_actor_to_entity(self.root_initiator),
            parent_job_id=self.parent_job_id,
            requested_at=ensure_datetime_utc(self.requested_at or get_datetime_utc()),
            started_at=ensure_datetime_utc(self.started_at)
            if self.started_at is not None
            else None,
            finished_at=ensure_datetime_utc(self.finished_at)
            if self.finished_at is not None
            else None,
            error=_error_to_entity(self.error),
        )

    @staticmethod
    def from_entity(job: Job) -> JobDTO:
        """Build a persistence DTO from a domain entity."""
        return JobDTO(
            id=job.id,
            name=job.name,
            input=job.input,
            status=job.status.value,
            stage=_stage_to_record(job.stage),
            result_summary=job.result_summary,
            root_initiator=_actor_to_record(job.root_initiator),
            parent_job_id=job.parent_job_id,
            requested_at=job.requested_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error=_error_to_record(job.error),
        )


def _stage_to_entity(stage: dict | None) -> JobStage | None:
    if stage is None:
        return None
    return JobStage(
        key=stage["key"],
        current=stage.get("current"),
        total=stage.get("total"),
        message=stage.get("message"),
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
        "data": _data_to_record(stage.data),
    }


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
