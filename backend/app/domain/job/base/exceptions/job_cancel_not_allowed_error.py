"""Job cancellation not allowed error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_cancel_error import JobCancelError


class JobCancelNotAllowedError(JobCancelError):
    """Raised when the job cannot be cancelled."""

    detail = "Job was not cancelled."
