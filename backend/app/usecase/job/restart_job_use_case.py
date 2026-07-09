"""Restart job application use case."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, cast

from app.domain.job import (
    Job,
    JobId,
    JobNotFoundError,
    JobRepository,
    JobRestartAccessDeniedError,
    JobRestartNotAllowedError,
    JobRestartNotFoundError,
    JobStatus,
)
from app.domain.user.value_objects import UserId
from app.usecase.job.create_job_use_case import (
    CreateJobUseCase,
    new_create_job_use_case,
)


class RestartJobUseCase(ABC):
    """Define the application boundary for restarting jobs."""

    @abstractmethod
    async def execute(self, job_id: JobId, *, current_user_id: UserId) -> JobId:
        """Create a new pending job from an existing terminal job."""


class RestartJobUseCaseImpl(RestartJobUseCase):
    """Restart an owned terminal job by creating a new job instance."""

    def __init__(
        self,
        jobs: JobRepository,
        create_job: CreateJobUseCase,
    ) -> None:
        """Store use case dependencies."""
        self.jobs = jobs
        self.create_job = create_job

    async def execute(self, job_id: JobId, *, current_user_id: UserId) -> JobId:
        """Create a new pending job from an existing terminal job."""
        try:
            job = await self.jobs.get(job_id)
        except JobNotFoundError as error:
            raise JobRestartNotFoundError(str(job_id)) from error

        if job.initiator.external_id != str(current_user_id):
            raise JobRestartAccessDeniedError(str(job_id))
        if job.status not in _TERMINAL_STATUSES:
            raise JobRestartNotAllowedError(str(job_id))

        restarted = self._new_restart_job(job)
        await self.create_job.execute(restarted)
        return restarted.id

    def _new_restart_job(self, job: Job) -> Job:
        job_class = cast(type[Job[Any, Any]], type(job))
        return job_class.new(
            initiator=job.initiator,
            input=job.input,
            name=job.name,
            description=job.description,
            parent_job_id=job.id,
        )


def new_restart_job_use_case(jobs: JobRepository) -> RestartJobUseCase:
    """Instantiate the restart-job use case."""
    return RestartJobUseCaseImpl(
        jobs=jobs,
        create_job=new_create_job_use_case(jobs=jobs),
    )


_TERMINAL_STATUSES = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
