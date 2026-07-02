"""Define the JobEvent repository contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.job.base.entities import JobEvent


class JobEventRepository(ABC):
    """Persist job events."""

    @abstractmethod
    async def append(self, job_id: UUID, event: JobEvent) -> None:
        """Append a new job event."""

    @abstractmethod
    async def list_by_job(self, job_id: UUID) -> list[JobEvent]:
        """Return events for a job."""
