"""SQLModel implementation of the job event repository."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import JobEvent, JobEventRepository
from app.infrastructure.sqlmodel.job.job_event_dto import JobEventDTO


class JobEventRepositoryImpl(JobEventRepository):
    """Persist job events with SQLModel."""

    def __init__(self, session: AsyncSession):
        """Store the active SQLModel session."""
        self.session = session

    async def append(self, event: JobEvent) -> None:
        """Append a new job event."""
        self.session.add(JobEventDTO.from_entity(event))

    async def list_by_job(self, job_id: UUID) -> list[JobEvent]:
        """Return events for a job."""
        statement = (
            select(JobEventDTO)
            .where(JobEventDTO.job_id == job_id)
            .order_by(col(JobEventDTO.created_at).asc())
        )
        result = await self.session.exec(statement)
        return [event.to_entity() for event in result.all()]


def new_job_event_repository(session: AsyncSession) -> JobEventRepository:
    """Create a job event repository bound to the active session."""
    return JobEventRepositoryImpl(session)
