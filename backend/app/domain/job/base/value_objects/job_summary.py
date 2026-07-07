"""Define the job summary value object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.job.base.value_objects.initiator import Initiator
from app.domain.job.base.value_objects.job_id import JobId
from app.domain.job.base.value_objects.job_status import JobStatus


@dataclass(frozen=True)
class JobSummary:
    """Represent compact immutable job state for list/query flows."""

    id: JobId
    type: str
    version: str
    name: str | None
    status: JobStatus
    initiator: Initiator
    parent_job_id: JobId | None
    requested_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
