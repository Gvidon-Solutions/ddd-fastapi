"""Define the job summary value object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.job.base.value_objects.initiator import Initiator
from app.domain.job.base.value_objects.job_status import JobStatus


@dataclass(frozen=True)
class JobSummary:
    """Represent compact immutable job state for list/query flows."""

    id: UUID
    type: str
    version: str
    name: str | None
    status: JobStatus
    initiator: Initiator
    parent_job_id: UUID | None
    requested_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
