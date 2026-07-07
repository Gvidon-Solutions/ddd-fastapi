"""Job cancellation not found error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_cancel_error import JobCancelError


class JobCancelNotFoundError(JobCancelError):
    """Raised when the requested job does not exist."""

    detail = "Job not found."
