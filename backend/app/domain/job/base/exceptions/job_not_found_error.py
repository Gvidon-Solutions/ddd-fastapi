"""Job not found error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_read_error import JobReadError


class JobNotFoundError(JobReadError):
    """Raised when a job aggregate does not exist."""

    detail = "Job not found."
