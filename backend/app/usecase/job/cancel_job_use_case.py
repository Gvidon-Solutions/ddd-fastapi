"""Provide the use case for cancelling jobs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import UUID

from app.domain.job import JobError, JobRepository, JobStatus
from app.usecase.job.ports import JobQueue


class CancelJobUseCase(ABC):
    """Define the application boundary for cancelling jobs."""

    @abstractmethod
    async def execute(self, job_id: UUID) -> bool:
        """Cancel a queued or running job."""


class CancelJobUseCaseImpl(CancelJobUseCase):
    """Cancel a queued or running job and persist the domain status."""

    def __init__(
        self,
        jobs: JobRepository,
        queue: JobQueue,
    ):
        """Store use case dependencies."""
        self.jobs = jobs
        self.queue = queue

    async def execute(self, job_id: UUID) -> bool:
        """Cancel a queued or running job."""
        cancelled = await self.queue.cancel(job_id)
        if not cancelled:
            return False

        job = await self.jobs.get(job_id)
        now = _now()
        job.job_status = JobStatus.CANCELLED
        job.updated_at = now
        job.finished_at = now
        job.job_error = JobError(
            code="CancelledError",
            message="Job cancelled",
        )
        await self.jobs.save(job)
        return True


def new_cancel_job_use_case(
    jobs: JobRepository,
    queue: JobQueue,
) -> CancelJobUseCase:
    """Instantiate the cancel job use case."""
    return CancelJobUseCaseImpl(
        jobs=jobs,
        queue=queue,
    )


def _now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)
