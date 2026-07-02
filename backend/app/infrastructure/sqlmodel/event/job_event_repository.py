"""SQLModel implementation of the job event repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import JobEvent, JobEventRepository
from app.infrastructure.sqlmodel.event.event_dto import EventDTO, JobEventLinkDTO


class JobEventRepositoryImpl(JobEventRepository):
    """Persist job events with SQLModel."""

    def __init__(self, session: AsyncSession):
        """Store the active SQLModel session."""
        self.session = session

    async def append(self, job_id: UUID, event: JobEvent) -> None:
        """Append a new job event."""
        self.session.add(EventDTO.from_job_event(event))
        sequence = await self._next_sequence(job_id)
        self.session.add(
            JobEventLinkDTO(
                job_id=job_id,
                event_id=event.event_id,
                relation="emitted",
                sequence=sequence,
                created_at=event.created_at,
            )
        )

    async def list_by_job(self, job_id: UUID) -> list[JobEvent]:
        """Return events for a job."""
        statement = (
            select(EventDTO)
            .join(JobEventLinkDTO, JobEventLinkDTO.event_id == EventDTO.event_id)
            .where(JobEventLinkDTO.job_id == job_id)
            .order_by(col(JobEventLinkDTO.sequence).asc())
        )
        result = await self.session.exec(statement)
        return [event.to_entity() for event in result.all()]

    async def _next_sequence(self, job_id: UUID) -> int:
        statement = select(func.max(JobEventLinkDTO.sequence)).where(
            JobEventLinkDTO.job_id == job_id
        )
        result = await self.session.exec(statement)
        return (result.one() or 0) + 1


def new_job_event_repository(session: AsyncSession) -> JobEventRepository:
    """Create a job event repository bound to the active session."""
    return JobEventRepositoryImpl(session)
