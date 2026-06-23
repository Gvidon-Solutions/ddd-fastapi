"""SQLModel implementation of the job repository."""

from __future__ import annotations

from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import Job, JobRepository
from app.infrastructure.sqlmodel.job.job_dto import JobDTO


class JobRepositoryImpl(JobRepository):
    """Persist jobs with SQLModel."""

    def __init__(self, session: AsyncSession):
        """Store the active SQLModel session."""
        self.session = session

    async def create(self, job: Job) -> None:
        """Create a new job."""
        self.session.add(JobDTO.from_entity(job))

    async def get(self, job_id: UUID) -> Job:
        """Return a job by ID."""
        job = await self.session.get(JobDTO, job_id)
        if job is None:
            raise KeyError(str(job_id))
        return job.to_entity()

    async def save(self, job: Job) -> None:
        """Persist changes to an existing job."""
        job_dto = JobDTO.from_entity(job)
        existing_job = await self.session.get(JobDTO, job.id)
        if existing_job is None:
            self.session.add(job_dto)
            return

        existing_job.name = job_dto.name
        existing_job.input = job_dto.input
        existing_job.status = job_dto.status
        existing_job.stage = job_dto.stage
        existing_job.result_summary = job_dto.result_summary
        existing_job.root_initiator = job_dto.root_initiator
        existing_job.parent_job_id = job_dto.parent_job_id
        existing_job.requested_at = job_dto.requested_at
        existing_job.started_at = job_dto.started_at
        existing_job.finished_at = job_dto.finished_at
        existing_job.error = job_dto.error
        self.session.add(existing_job)


def new_job_repository(session: AsyncSession) -> JobRepository:
    """Create a job repository bound to the active session."""
    return JobRepositoryImpl(session)
