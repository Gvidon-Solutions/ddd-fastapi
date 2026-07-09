"""Delete job application use case."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.job import (
    JobDeleteAccessDeniedError,
    JobDeleteNotAllowedError,
    JobDeleteNotFoundError,
    JobId,
    JobNotFoundError,
    JobRepository,
    JobStatus,
    JobSummary,
)
from app.domain.user.value_objects import UserId


class DeleteJobUseCase(ABC):
    """Define the application boundary for deleting jobs."""

    @abstractmethod
    async def execute(
        self,
        job_id: JobId,
        *,
        current_user_id: UserId,
    ) -> None:
        """Delete a job and its descendants visible to the current user."""


class DeleteJobUseCaseImpl(DeleteJobUseCase):
    """Delete an owned terminal job and all owned terminal descendants."""

    def __init__(self, jobs: JobRepository) -> None:
        """Store use case dependencies."""
        self.jobs = jobs

    async def execute(
        self,
        job_id: JobId,
        *,
        current_user_id: UserId,
    ) -> None:
        """Delete a job and its descendants visible to the current user."""
        try:
            job = await self.jobs.get(job_id)
        except JobNotFoundError as error:
            raise JobDeleteNotFoundError(str(job_id)) from error

        if job.initiator.external_id != str(current_user_id):
            raise JobDeleteAccessDeniedError(str(job_id))
        self._assert_terminal(job_id=job.id, status=job.status)

        await self._assert_descendants_deletable(
            job_id,
            current_user_id=current_user_id,
        )

        try:
            await self.jobs.delete(job_id, cascade_children=True)
        except JobNotFoundError as error:
            raise JobDeleteNotFoundError(str(job_id)) from error

    async def _assert_descendants_deletable(
        self,
        parent_job_id: JobId,
        *,
        current_user_id: UserId,
    ) -> None:
        children = await self.jobs.list_children(parent_job_id)
        for child in children:
            self._assert_owned(child, current_user_id=current_user_id)
            self._assert_terminal(job_id=child.id, status=child.status)
            await self._assert_descendants_deletable(
                child.id,
                current_user_id=current_user_id,
            )

    def _assert_owned(self, job: JobSummary, *, current_user_id: UserId) -> None:
        if job.initiator.external_id != str(current_user_id):
            raise JobDeleteAccessDeniedError(str(job.id))

    def _assert_terminal(self, *, job_id: JobId, status: JobStatus) -> None:
        if status not in _TERMINAL_STATUSES:
            raise JobDeleteNotAllowedError(str(job_id))


def new_delete_job_use_case(jobs: JobRepository) -> DeleteJobUseCase:
    """Instantiate the delete-job use case."""
    return DeleteJobUseCaseImpl(jobs=jobs)


_TERMINAL_STATUSES = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
