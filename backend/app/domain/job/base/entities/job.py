"""Define the generic Job entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar
from uuid import UUID

from app.domain.job.base.value_objects import Initiator, JobError, JobStatus

InputT = TypeVar("InputT")
ResultT = TypeVar("ResultT")


@dataclass
class Job[InputT, ResultT]:
    """Represent one execution of a versioned job contract."""

    id: UUID
    type: str
    version: str
    name: str | None
    description: str | None
    input: InputT
    result: ResultT | None
    status: JobStatus
    initiator: Initiator
    parent_job_id: UUID | None
    requested_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: JobError | None
    dispatch_attempts: int = 0
    next_dispatch_at: datetime | None = None
    last_dispatch_error: str | None = None
    dispatched_at: datetime | None = None


type AnyJob = Job[object, object]
