"""Job restart not allowed error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_restart_error import JobRestartError


class JobRestartNotAllowedError(JobRestartError):
    """Raised when the job cannot be restarted."""

    detail = "Only terminal jobs can be restarted."
