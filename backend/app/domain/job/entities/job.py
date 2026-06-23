"""Define the Job entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.job.value_objects import Actor, JobError, JobStage, JobStatus


@dataclass
class Job:
    """Represent a concrete execution run."""

    id: UUID
    name: str
    input: dict | None
    status: JobStatus
    stage: JobStage | None
    result_summary: dict | None
    root_initiator: Actor
    parent_job_id: UUID | None
    requested_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: JobError | None
