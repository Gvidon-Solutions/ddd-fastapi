"""Get job details application use case."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.job import (
    JobDetails,
    JobReadAccessDeniedError,
    JobReadNotFoundError,
    JobRepository,
)


class GetJobDetailsUseCase(ABC):
    """Define the application boundary for reading one job."""

    @abstractmethod
    async def execute(self, job_id: UUID, *, current_user_id: str) -> JobDetails:
        """Return job details visible to the current user."""


class GetJobDetailsUseCaseImpl(GetJobDetailsUseCase):
    """Read one job owned by the current user."""

    def __init__(self, jobs: JobRepository) -> None:
        """Store use case dependencies."""
        self.jobs = jobs

    async def execute(self, job_id: UUID, *, current_user_id: str) -> JobDetails:
        """Return job details visible to the current user."""
        try:
            details = await self.jobs.get_detail(job_id)
        except KeyError as error:
            raise JobReadNotFoundError(str(job_id)) from error

        if details.initiator.external_id != current_user_id:
            raise JobReadAccessDeniedError(str(job_id))
        return details


def new_get_job_details_use_case(jobs: JobRepository) -> GetJobDetailsUseCase:
    """Instantiate the get-job-details use case."""
    return GetJobDetailsUseCaseImpl(jobs=jobs)
