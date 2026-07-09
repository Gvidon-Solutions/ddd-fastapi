"""Job await timeout error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_read_error import JobReadError


class JobAwaitTimeoutError(JobReadError):
    """Raised when a job does not reach a terminal status before timeout."""

    detail = "Job did not reach a terminal status before timeout."
