"""Job deletion access denied error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_delete_error import JobDeleteError


class JobDeleteAccessDeniedError(JobDeleteError):
    """Raised when the current user cannot delete the job."""

    detail = "Job deletion access denied."
