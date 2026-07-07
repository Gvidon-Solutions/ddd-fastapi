"""Provide the use case for cancelling jobs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from app.domain.job import (
    JobCancelAccessDeniedError,
    JobCancelNotAllowedError,
    JobCancelNotFoundError,
    JobError,
    JobId,
    JobRepository,
    JobStatus,
)
from app.domain.user.value_objects import UserId
from app.usecase.job.ports import JobRuntime


class CancelJobUseCase(ABC):
    """Define the application boundary for cancelling jobs."""

    @abstractmethod
    async def execute(self, job_id: JobId, *, current_user_id: UserId) -> None:
        """Cancel a pending, queued, or running job."""


class CancelJobUseCaseImpl(CancelJobUseCase):
    """Cancel a pending, queued, or running job and persist the domain status."""

    def __init__(
        self,
        jobs: JobRepository,
        runtime: JobRuntime,
    ):
        """Store use case dependencies."""
        self.jobs = jobs
        self.runtime = runtime

    async def execute(self, job_id: JobId, *, current_user_id: UserId) -> None:
        """Cancel a pending, queued, or running job."""
        try:
            job = await self.jobs.get(job_id)
        except KeyError:
            raise JobCancelNotFoundError(str(job_id))

        if job.initiator.external_id != str(current_user_id):
            raise JobCancelAccessDeniedError(str(job_id))

        if job.status == JobStatus.RUNNING:
            await self.runtime.request_cancel(job_id)
            if not await self.runtime.cancel(job_id):
                raise JobCancelNotAllowedError(str(job_id))
            return

        if job.status == JobStatus.PENDING:
            await self._mark_cancelled_without_worker(job_id)
            return

        if job.status == JobStatus.QUEUED:
            if not await self.runtime.cancel(job_id):
                raise JobCancelNotAllowedError(str(job_id))
            await self._mark_cancelled_without_worker(job_id)
            return

        raise JobCancelNotAllowedError(str(job_id))

    async def _mark_cancelled_without_worker(self, job_id: JobId) -> None:
        if await self.jobs.try_mark_cancelled(
            job_id,
            error=JobError(
                code="CancelledError",
                message="Job cancelled",
            ),
            finished_at=_now(),
        ):
            return
        raise JobCancelNotAllowedError(str(job_id))


def new_cancel_job_use_case(
    jobs: JobRepository,
    runtime: JobRuntime,
) -> CancelJobUseCase:
    """Instantiate the cancel job use case."""
    return CancelJobUseCaseImpl(
        jobs=jobs,
        runtime=runtime,
    )


def _now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)
