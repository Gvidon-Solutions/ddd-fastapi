"""Job restart not found error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_restart_error import JobRestartError


class JobRestartNotFoundError(JobRestartError):
    """Raised when the job being restarted does not exist."""

    detail = "Job not found."
