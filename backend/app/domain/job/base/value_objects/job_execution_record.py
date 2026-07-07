"""Define raw job execution record value object."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.job.base.value_objects.job_status import JobStatus


@dataclass(frozen=True)
class JobExecutionRecord:
    """Raw job data needed by the execution boundary."""

    job_id: UUID
    type: str
    version: str
    input: dict
    status: JobStatus
