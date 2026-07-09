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
    JobNotFoundError,
    JobRepository,
    JobStatus,
    JobSummary,
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
        except JobNotFoundError:
            raise JobCancelNotFoundError(str(job_id))

        if job.initiator.external_id != str(current_user_id):
            raise JobCancelAccessDeniedError(str(job_id))

        await self._cancel_descendants(job_id)
        await self._cancel_job(job_id=job.id, status=job.status, require_active=True)

    async def _cancel_descendants(self, parent_job_id: JobId) -> None:
        children = await self.jobs.list_children(parent_job_id)
        for child in children:
            await self._cancel_descendants(child.id)
            await self._cancel_child(child)

    async def _cancel_child(self, job: JobSummary) -> None:
        if job.status in _TERMINAL_STATUSES:
            return
        await self._cancel_job(job_id=job.id, status=job.status, require_active=False)

    async def _cancel_job(
        self,
        *,
        job_id: JobId,
        status: JobStatus,
        require_active: bool,
    ) -> None:
        if status == JobStatus.RUNNING:
            await self.runtime.request_cancel(job_id)
            if not await self.runtime.cancel(job_id):
                raise JobCancelNotAllowedError(str(job_id))
            return

        if status == JobStatus.PENDING:
            await self._mark_cancelled_without_worker(job_id)
            return

        if status == JobStatus.QUEUED:
            if not await self.runtime.cancel(job_id):
                raise JobCancelNotAllowedError(str(job_id))
            await self._mark_cancelled_without_worker(job_id)
            return

        if not require_active:
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


_TERMINAL_STATUSES = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
