"""Define the JobFile association entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.file import File
from app.domain.job.base.value_objects import JobFileRole, JobId


@dataclass(frozen=True)
class JobFile(File):
    """Represent a stored file associated with a specific job."""

    job_id: JobId
    role: JobFileRole
    description: str | None
    attached_at: datetime
