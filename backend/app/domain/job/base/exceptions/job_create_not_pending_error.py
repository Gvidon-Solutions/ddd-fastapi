"""Job creation pending-status error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_create_error import JobCreateError


class JobCreateNotPendingError(JobCreateError):
    """Raised when a job is not pending before creation."""

    detail = "Job must be pending before creation."
