"""Provide the use case for cancelling jobs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import UUID

from app.domain.job import JobError, JobRepository, JobStatus
from app.usecase.job.ports import JobCancellationBackend, JobQueue


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
        cancellation_backend: JobCancellationBackend | None = None,
    ):
        """Store use case dependencies."""
        self.jobs = jobs
        self.queue = queue
        self.cancellation_backend = cancellation_backend

    async def execute(self, job_id: UUID) -> bool:
        """Cancel a queued or running job."""
        try:
            job = await self.jobs.get(job_id)
        except KeyError:
            return await self.queue.cancel(job_id)

        if job.status == JobStatus.RUNNING and self.cancellation_backend is not None:
            await self.cancellation_backend.request_cancel(job_id)
            await self.queue.cancel(job_id)
            return True

        if job.status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
            return False

        cancelled = await self.queue.cancel(job_id)
        if not cancelled:
            return False

        now = _now()
        try:
            return await self.jobs.try_mark_cancelled(
                job_id,
                error=JobError(
                    code="CancelledError",
                    message="Job cancelled",
                ),
                finished_at=now,
            )
        except NotImplementedError:
            pass

        job.status = JobStatus.CANCELLED
        job.updated_at = now
        job.finished_at = now
        job.error = JobError(
            code="CancelledError",
            message="Job cancelled",
        )
        await self.jobs.save(job)
        return True


def new_cancel_job_use_case(
    jobs: JobRepository,
    queue: JobQueue,
    cancellation_backend: JobCancellationBackend | None = None,
) -> CancelJobUseCase:
    """Instantiate the cancel job use case."""
    return CancelJobUseCaseImpl(
        jobs=jobs,
        queue=queue,
        cancellation_backend=cancellation_backend,
    )


def _now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)
