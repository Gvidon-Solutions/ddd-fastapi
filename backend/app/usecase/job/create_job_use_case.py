"""Create typed jobs by persisting them for dispatch."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.job import (
    Job,
    JobCreateNotPendingError,
    JobRepository,
    JobStatus,
    UnknownJobContractError,
    get_job_class,
)


class CreateJobUseCase(ABC):
    """Use case for creating already constructed typed jobs."""

    @abstractmethod
    async def execute(self, job: Job) -> None:
        """Persist a pending job for dispatcher pickup."""


class CreateJobUseCaseImpl(CreateJobUseCase):
    """Create jobs for dispatcher pickup."""

    def __init__(
        self,
        jobs: JobRepository,
    ) -> None:
        """Store use case dependencies."""
        self.jobs = jobs

    async def execute(self, job: Job) -> None:
        """Persist a pending job for dispatcher pickup."""
        if get_job_class(type=job.type, version=job.version) is None:
            raise UnknownJobContractError(
                f"Unknown job contract: {job.type} {job.version}"
            )
        if job.status != JobStatus.PENDING:
            raise JobCreateNotPendingError()
        await self.jobs.create(job)


def new_create_job_use_case(
    jobs: JobRepository,
) -> CreateJobUseCase:
    """Create the create-job use case."""
    return CreateJobUseCaseImpl(jobs=jobs)
