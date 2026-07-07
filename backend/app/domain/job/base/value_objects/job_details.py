"""Define the job details value object."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.job.base.entities import JobEvent, JobFile
from app.domain.job.base.value_objects.job_error import JobError
from app.domain.job.base.value_objects.job_summary import JobSummary


@dataclass(frozen=True)
class JobDetails(JobSummary):
    """Represent full immutable job state for read flows."""

    input: object
    result: object | None
    error: JobError | None
    files: tuple[JobFile, ...]
    events: tuple[JobEvent, ...]
