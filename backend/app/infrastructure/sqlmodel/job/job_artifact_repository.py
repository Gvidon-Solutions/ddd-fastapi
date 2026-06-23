"""SQLModel implementation of the job artifact repository."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import ArtifactRole, JobArtifact, JobArtifactRepository
from app.infrastructure.sqlmodel.job.job_artifact_dto import JobArtifactDTO


class JobArtifactRepositoryImpl(JobArtifactRepository):
    """Persist job artifacts with SQLModel."""

    def __init__(self, session: AsyncSession):
        """Store the active SQLModel session."""
        self.session = session

    async def create(self, artifact: JobArtifact) -> None:
        """Create a new artifact."""
        self.session.add(JobArtifactDTO.from_entity(artifact))

    async def list_by_job(
        self,
        job_id: UUID,
        role: ArtifactRole | None = None,
    ) -> list[JobArtifact]:
        """Return artifacts for a job."""
        statement = select(JobArtifactDTO).where(JobArtifactDTO.job_id == job_id)
        if role is not None:
            statement = statement.where(JobArtifactDTO.role == role.value)
        statement = statement.order_by(col(JobArtifactDTO.created_at).asc())
        result = await self.session.exec(statement)
        return [artifact.to_entity() for artifact in result.all()]


def new_job_artifact_repository(session: AsyncSession) -> JobArtifactRepository:
    """Create a job artifact repository bound to the active session."""
    return JobArtifactRepositoryImpl(session)
