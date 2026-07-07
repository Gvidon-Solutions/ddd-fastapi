"""List jobs application use case."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.job import JobRepository, JobSummary
from app.domain.user.value_objects import UserId


class ListJobsUseCase(ABC):
    """Define the application boundary for listing jobs."""

    @abstractmethod
    async def execute(self, *, current_user_id: UserId) -> list[JobSummary]:
        """Return job summaries visible to the current user."""


class ListJobsUseCaseImpl(ListJobsUseCase):
    """List jobs owned by the current user."""

    def __init__(self, jobs: JobRepository) -> None:
        """Store use case dependencies."""
        self.jobs = jobs

    async def execute(self, *, current_user_id: UserId) -> list[JobSummary]:
        """Return job summaries visible to the current user."""
        return await self.jobs.list_by_initiator(str(current_user_id))


def new_list_jobs_use_case(jobs: JobRepository) -> ListJobsUseCase:
    """Instantiate the list-jobs use case."""
    return ListJobsUseCaseImpl(jobs=jobs)
