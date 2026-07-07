"""Job deletion not allowed error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_delete_error import JobDeleteError


class JobDeleteNotAllowedError(JobDeleteError):
    """Raised when a non-terminal job is deleted."""

    detail = "Only terminal jobs can be deleted."
