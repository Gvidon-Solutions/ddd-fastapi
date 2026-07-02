"""Define the JobFile repository contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.job.base.entities import JobFile
from app.domain.job.base.value_objects import JobFileRole


class JobFileRepository(ABC):
    """Persist job-file associations."""

    @abstractmethod
    async def create(self, job_file: JobFile) -> None:
        """Create a job-file association."""

    @abstractmethod
    async def list_by_job(
        self,
        job_id: UUID,
        role: JobFileRole | None = None,
    ) -> list[JobFile]:
        """Return files associated with a job."""
