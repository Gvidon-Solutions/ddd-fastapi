"""Job read access denied error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_read_error import JobReadError


class JobReadAccessDeniedError(JobReadError):
    """Raised when the current user cannot read the job."""

    detail = "Job access denied."
