"""Job cancellation access denied error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_cancel_error import JobCancelError


class JobCancelAccessDeniedError(JobCancelError):
    """Raised when the current user cannot cancel the job."""

    detail = "Job access denied."
