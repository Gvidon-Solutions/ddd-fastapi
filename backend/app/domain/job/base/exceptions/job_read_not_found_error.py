"""Job read not found error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_read_error import JobReadError


class JobReadNotFoundError(JobReadError):
    """Raised when the requested job does not exist."""

    detail = "Job not found."
