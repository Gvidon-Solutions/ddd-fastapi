"""Define raw job execution record value object."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.job.base.value_objects.job_id import JobId
from app.domain.job.base.value_objects.job_status import JobStatus


@dataclass(frozen=True)
class JobExecutionRecord:
    """Raw job data needed by the execution boundary."""

    job_id: JobId
    type: str
    version: str
    input: dict
    status: JobStatus
