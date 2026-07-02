"""SQLModel implementation of the job repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import (
    AnyJob,
    Job,
    JobError,
    JobExecutionRecord,
    JobRepository,
    JobStatus,
)
from app.infrastructure.sqlmodel.job.job_dto import JobDTO, _error_to_record, _to_record


class JobRepositoryImpl(JobRepository):
    """Persist jobs with SQLModel."""

    def __init__(self, session: AsyncSession):
        """Store the active SQLModel session."""
        self.session = session

    async def create(self, job: Job) -> None:
        """Create a new job."""
        self.session.add(JobDTO.from_entity(job))

    async def get(self, job_id: UUID) -> AnyJob:
        """Return a job by ID."""
        job = await self.session.get(JobDTO, job_id)
        if job is None:
            raise KeyError(str(job_id))
        return job.to_entity()

    async def save(self, job: Job) -> None:
        """Persist metadata changes to an existing job."""
        job_dto = JobDTO.from_entity(job)
        existing_job = await self.session.get(JobDTO, job.id)
        if existing_job is None:
            self.session.add(job_dto)
            return

        existing_job.type = job_dto.type
        existing_job.version = job_dto.version
        existing_job.name = job_dto.name
        existing_job.description = job_dto.description
        existing_job.input = job_dto.input
        existing_job.result = job_dto.result
        existing_job.status = job_dto.status
        existing_job.initiator = job_dto.initiator
        existing_job.parent_job_id = job_dto.parent_job_id
        existing_job.requested_at = job_dto.requested_at
        existing_job.updated_at = job_dto.updated_at
        existing_job.started_at = job_dto.started_at
        existing_job.finished_at = job_dto.finished_at
        existing_job.error = job_dto.error
        self.session.add(existing_job)

    async def get_execution_record(self, job_id: UUID) -> JobExecutionRecord:
        """Return raw execution data without typed deserialization."""
        job = await self.session.get(JobDTO, job_id)
        if job is None:
            raise KeyError(str(job_id))
        return JobExecutionRecord(
            job_id=job.job_id,
            type=job.type,
            version=job.version,
            input=job.input,
            status=JobStatus(job.status),
        )

    async def try_mark_running(
        self,
        job_id: UUID,
        *,
        started_at: datetime,
    ) -> bool:
        """Atomically mark a queued job as running."""
        return await self._transition(
            job_id,
            expected=JobStatus.QUEUED,
            values={
                "status": JobStatus.RUNNING.value,
                "started_at": started_at,
                "updated_at": started_at,
            },
        )

    async def try_mark_succeeded(
        self,
        job_id: UUID,
        *,
        result: object,
        finished_at: datetime,
    ) -> bool:
        """Atomically mark a running job as succeeded."""
        return await self._transition(
            job_id,
            expected=JobStatus.RUNNING,
            values={
                "status": JobStatus.SUCCEEDED.value,
                "result": _to_record(result),
                "error": None,
                "finished_at": finished_at,
                "updated_at": finished_at,
            },
        )

    async def try_mark_failed(
        self,
        job_id: UUID,
        *,
        error: JobError,
        finished_at: datetime,
    ) -> bool:
        """Atomically mark a running job as failed."""
        return await self._transition(
            job_id,
            expected=JobStatus.RUNNING,
            values={
                "status": JobStatus.FAILED.value,
                "result": None,
                "error": _error_to_record(error),
                "finished_at": finished_at,
                "updated_at": finished_at,
            },
        )

    async def try_mark_cancelled(
        self,
        job_id: UUID,
        *,
        error: JobError,
        finished_at: datetime,
    ) -> bool:
        """Atomically mark a queued or running job as cancelled."""
        statement = (
            update(JobDTO)
            .where(
                JobDTO.job_id == job_id,
                JobDTO.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value]),
            )
            .values(
                status=JobStatus.CANCELLED.value,
                result=None,
                error=_error_to_record(error),
                finished_at=finished_at,
                updated_at=finished_at,
            )
        )
        result = await self.session.exec(statement)
        return (result.rowcount or 0) == 1

    async def _transition(
        self,
        job_id: UUID,
        *,
        expected: JobStatus,
        values: dict,
    ) -> bool:
        statement = (
            update(JobDTO)
            .where(JobDTO.job_id == job_id, JobDTO.status == expected.value)
            .values(**values)
        )
        result = await self.session.exec(statement)
        return (result.rowcount or 0) == 1


def new_job_repository(session: AsyncSession) -> JobRepository:
    """Create a job repository bound to the active session."""
    return JobRepositoryImpl(session)
