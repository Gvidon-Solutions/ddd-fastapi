"""Define the Job repository contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.job.base.entities import AnyJob, Job
from app.domain.job.base.value_objects import JobError, JobStatus


@dataclass(frozen=True)
class JobExecutionRecord:
    """Raw job data needed by the execution boundary."""

    job_id: UUID
    type: str
    version: str
    input: dict
    status: JobStatus


class JobRepository(ABC):
    """Persist jobs."""

    @abstractmethod
    async def create(self, job: Job) -> None:
        """Create a new job."""

    @abstractmethod
    async def get(self, job_id: UUID) -> AnyJob:
        """Return a job by ID."""

    @abstractmethod
    async def save(self, job: Job) -> None:
        """Persist changes to an existing job."""

    async def get_execution_record(self, job_id: UUID) -> JobExecutionRecord:
        """Return raw execution data without typed deserialization."""
        raise NotImplementedError

    async def try_mark_running(
        self,
        job_id: UUID,
        *,
        started_at: datetime,
    ) -> bool:
        """Atomically mark a queued job as running."""
        raise NotImplementedError

    async def try_mark_succeeded(
        self,
        job_id: UUID,
        *,
        result: object,
        finished_at: datetime,
    ) -> bool:
        """Atomically mark a running job as succeeded."""
        raise NotImplementedError

    async def try_mark_failed(
        self,
        job_id: UUID,
        *,
        error: JobError,
        finished_at: datetime,
    ) -> bool:
        """Atomically mark a running job as failed."""
        raise NotImplementedError

    async def try_mark_cancelled(
        self,
        job_id: UUID,
        *,
        error: JobError,
        finished_at: datetime,
    ) -> bool:
        """Atomically mark a running or queued job as cancelled."""
        raise NotImplementedError
