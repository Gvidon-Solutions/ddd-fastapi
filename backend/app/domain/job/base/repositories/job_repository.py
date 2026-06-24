"""Define the Job repository contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.job.base.entities import Job


class JobRepository(ABC):
    """Persist jobs."""

    @abstractmethod
    async def create(self, job: Job) -> None:
        """Create a new job."""

    @abstractmethod
    async def get(self, job_id: UUID) -> Job:
        """Return a job by ID."""

    @abstractmethod
    async def save(self, job: Job) -> None:
        """Persist changes to an existing job."""
