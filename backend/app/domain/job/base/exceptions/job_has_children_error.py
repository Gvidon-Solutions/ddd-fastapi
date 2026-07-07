"""Job has children error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_delete_error import JobDeleteError


class JobHasChildrenError(JobDeleteError):
    """Raised when a job has children and cascade deletion is disabled."""

    detail = "Job has child jobs."
