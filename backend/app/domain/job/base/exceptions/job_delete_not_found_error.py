"""Job deletion not found error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_delete_error import JobDeleteError


class JobDeleteNotFoundError(JobDeleteError):
    """Raised when the job being deleted does not exist."""

    detail = "Job not found."
