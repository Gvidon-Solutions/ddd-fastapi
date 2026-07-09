"""Job restart access denied error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_restart_error import JobRestartError


class JobRestartAccessDeniedError(JobRestartError):
    """Raised when the current user cannot restart the job."""

    detail = "Job restart access denied."
