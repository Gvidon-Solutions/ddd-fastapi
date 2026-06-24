"""Define the Job entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.job.base.value_objects import Actor, JobError, JobStage, JobStatus


@dataclass
class Job:
    """Represent a concrete execution run."""

    job_id: UUID
    job_type: str
    job_name: str
    job_description: str | None
    job_input: dict | None
    job_status: JobStatus
    job_stage: JobStage | None
    result_summary: dict | None
    root_initiator: Actor
    parent_job_id: UUID | None
    requested_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    job_error: JobError | None
