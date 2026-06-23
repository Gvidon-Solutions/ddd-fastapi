"""Provide the use case for launching jobs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID, uuid4

from app.domain.job import Actor, Job, JobRepository, JobStatus
from app.usecase.job.ports import Clock, JobQueue


class LaunchJobUseCase(ABC):
    """Define the application boundary for launching jobs."""

    @abstractmethod
    async def execute(
        self,
        name: str,
        root_initiator: Actor,
        input: dict | None = None,
        parent_job_id: UUID | None = None,
    ) -> UUID:
        """Create a queued job, enqueue it, and return its ID."""


class LaunchJobUseCaseImpl(LaunchJobUseCase):
    """Create a queued job and dispatch it to the queue."""

    def __init__(
        self,
        jobs: JobRepository,
        queue: JobQueue,
        clock: Clock,
    ):
        """Store use case dependencies."""
        self.jobs = jobs
        self.queue = queue
        self.clock = clock

    async def execute(
        self,
        name: str,
        root_initiator: Actor,
        input: dict | None = None,
        parent_job_id: UUID | None = None,
    ) -> UUID:
        """Create a queued job, enqueue it, and return its ID."""
        job = Job(
            id=uuid4(),
            name=name,
            input=input,
            status=JobStatus.QUEUED,
            stage=None,
            result_summary=None,
            root_initiator=root_initiator,
            parent_job_id=parent_job_id,
            requested_at=self.clock.now(),
            started_at=None,
            finished_at=None,
            error=None,
        )

        await self.jobs.create(job)
        await self.queue.enqueue(
            job_name=job.name,
            job_id=job.id,
        )

        return job.id


def new_launch_job_use_case(
    jobs: JobRepository,
    queue: JobQueue,
    clock: Clock,
) -> LaunchJobUseCase:
    """Instantiate the launch job use case."""
    return LaunchJobUseCaseImpl(
        jobs=jobs,
        queue=queue,
        clock=clock,
    )
