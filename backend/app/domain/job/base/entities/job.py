"""Define the generic Job entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self, TypeVar

from app.domain.job.base.value_objects import (
    Initiator,
    JobError,
    JobId,
    JobStatus,
    new_job_id,
)

InputT = TypeVar("InputT")
ResultT = TypeVar("ResultT")


@dataclass
class Job[InputT, ResultT]:
    """Represent one execution of a versioned job contract."""

    id: JobId
    type: str
    version: str
    name: str | None
    description: str | None
    input: InputT
    result: ResultT | None
    status: JobStatus
    initiator: Initiator
    parent_job_id: JobId | None
    requested_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: JobError | None
    dispatch_attempts: int = 0
    next_dispatch_at: datetime | None = None
    last_dispatch_error: str | None = None
    dispatched_at: datetime | None = None

    @classmethod
    def new(
        cls,
        *,
        initiator: Initiator,
        input: InputT,
        name: str | None = None,
        description: str | None = None,
        parent_job_id: JobId | None = None,
    ) -> Self:
        """Create a pending job instance for this typed job entity."""
        input_type = getattr(cls, "input", None)
        if not isinstance(input_type, type):
            raise TypeError(f"{cls.__name__} must define an input type")
        if not isinstance(input, input_type):
            raise TypeError(f"{cls.type} {cls.version} requires {input_type.__name__}")

        now = datetime.now(UTC)
        return cls(
            id=new_job_id(),
            type=cls.type,
            version=cls.version,
            name=name,
            description=description,
            input=input,
            result=None,
            status=JobStatus.PENDING,
            initiator=initiator,
            parent_job_id=parent_job_id,
            requested_at=now,
            updated_at=now,
            started_at=None,
            finished_at=None,
            error=None,
            dispatch_attempts=0,
            next_dispatch_at=now,
            last_dispatch_error=None,
            dispatched_at=None,
        )


type AnyJob = Job[object, object]
