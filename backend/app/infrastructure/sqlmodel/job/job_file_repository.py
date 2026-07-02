"""SQLModel implementation of the job-file repository."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import JobFile, JobFileRepository, JobFileRole
from app.infrastructure.sqlmodel.job.file_dto import FileDTO
from app.infrastructure.sqlmodel.job.job_file_dto import JobFileDTO


class JobFileRepositoryImpl(JobFileRepository):
    """Persist job-file associations with SQLModel."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, job_file: JobFile) -> None:
        """Create a job-file association."""
        self.session.add(FileDTO.from_entity(job_file.file))
        self.session.add(JobFileDTO.from_entity(job_file))

    async def list_by_job(
        self,
        job_id: UUID,
        role: JobFileRole | None = None,
    ) -> list[JobFile]:
        """Return files associated with a job."""
        statement = (
            select(JobFileDTO, FileDTO)
            .join(FileDTO, FileDTO.file_id == JobFileDTO.file_id)
            .where(JobFileDTO.job_id == job_id)
            .order_by(col(JobFileDTO.created_at).asc())
        )
        if role is not None:
            statement = statement.where(JobFileDTO.role == role.value)
        rows = (await self.session.exec(statement)).all()
        return [job_file.to_entity(file) for job_file, file in rows]


def new_job_file_repository(session: AsyncSession) -> JobFileRepository:
    """Create a job-file repository bound to the active session."""
    return JobFileRepositoryImpl(session)
