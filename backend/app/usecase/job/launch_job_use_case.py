"""Provide the use case for launching jobs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.job import Actor, Job, JobRepository, JobStatus
from app.usecase.job.ports import JobQueue


class LaunchJobUseCase(ABC):
    """Define the application boundary for launching jobs."""

    @abstractmethod
    async def execute(
        self,
        job_type: str,
        job_name: str,
        root_initiator: Actor,
        job_description: str | None = None,
        job_input: dict | None = None,
        parent_job_id: UUID | None = None,
    ) -> UUID:
        """Create a queued job, enqueue it, and return its ID."""


class LaunchJobUseCaseImpl(LaunchJobUseCase):
    """Create a queued job and dispatch it to the queue."""

    def __init__(
        self,
        jobs: JobRepository,
        queue: JobQueue,
    ):
        """Store use case dependencies."""
        self.jobs = jobs
        self.queue = queue

    async def execute(
        self,
        job_type: str,
        job_name: str,
        root_initiator: Actor,
        job_description: str | None = None,
        job_input: dict | None = None,
        parent_job_id: UUID | None = None,
    ) -> UUID:
        """Create a queued job, enqueue it, and return its ID."""
        now = _now()
        job = Job(
            job_id=uuid4(),
            job_type=job_type,
            job_name=job_name,
            job_description=job_description,
            job_input=job_input,
            job_status=JobStatus.QUEUED,
            job_stage=None,
            result_summary=None,
            root_initiator=root_initiator,
            parent_job_id=parent_job_id,
            requested_at=now,
            updated_at=now,
            started_at=None,
            finished_at=None,
            job_error=None,
        )

        await self.jobs.create(job)
        await self.queue.enqueue(
            job_type=job.job_type,
            job_id=job.job_id,
        )

        return job.job_id


def new_launch_job_use_case(
    jobs: JobRepository,
    queue: JobQueue,
) -> LaunchJobUseCase:
    """Instantiate the launch job use case."""
    return LaunchJobUseCaseImpl(
        jobs=jobs,
        queue=queue,
    )


def _now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)
