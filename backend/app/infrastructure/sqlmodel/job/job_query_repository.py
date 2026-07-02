"""SQLModel read-side job query repository."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import (
    JobDetailProjection,
    JobError,
    JobQueryRepository,
    JobStatus,
    JobSummary,
)
from app.infrastructure.sqlmodel.datetime import ensure_datetime_utc
from app.infrastructure.sqlmodel.event.job_event_repository import (
    JobEventRepositoryImpl,
)
from app.infrastructure.sqlmodel.job.initiator_dto import InitiatorDTO
from app.infrastructure.sqlmodel.job.job_dto import JobDTO
from app.infrastructure.sqlmodel.job.job_file_repository import JobFileRepositoryImpl


class JobQueryRepositoryImpl(JobQueryRepository):
    """Build job projections without typed input/result deserialization."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.job_files = JobFileRepositoryImpl(session)
        self.job_events = JobEventRepositoryImpl(session)

    async def get_detail(self, job_id: UUID) -> JobDetailProjection:
        """Return a job detail projection."""
        job = await self.session.get(JobDTO, job_id)
        if job is None:
            raise KeyError(str(job_id))
        summary = await self._summary(job)
        files = await self.job_files.list_by_job(job_id)
        events = await self.job_events.list_by_job(job_id)
        return JobDetailProjection(
            summary=summary,
            input=job.input,
            result=job.result,
            error=_error_to_entity(job.error),
            files=tuple(files),
            events=tuple(events),
        )

    async def list_by_initiator(self, initiator_external_id: str) -> list[JobSummary]:
        """Return jobs launched by an initiator external id."""
        statement = (
            select(JobDTO)
            .join(InitiatorDTO, InitiatorDTO.initiator_id == JobDTO.initiator_id)
            .where(InitiatorDTO.external_id == initiator_external_id)
            .order_by(col(JobDTO.requested_at).desc())
        )
        jobs = (await self.session.exec(statement)).all()
        return [await self._summary(job) for job in jobs]

    async def _summary(self, job: JobDTO) -> JobSummary:
        initiator = await self.session.get(InitiatorDTO, job.initiator_id)
        if initiator is None:
            raise KeyError(str(job.initiator_id))
        return JobSummary(
            id=job.job_id,
            type=job.type,
            version=job.version,
            name=job.name,
            status=JobStatus(job.status),
            initiator=initiator.to_value_object(),
            parent_job_id=job.parent_job_id,
            requested_at=ensure_datetime_utc(job.requested_at),
            updated_at=ensure_datetime_utc(job.updated_at),
            started_at=ensure_datetime_utc(job.started_at)
            if job.started_at is not None
            else None,
            finished_at=ensure_datetime_utc(job.finished_at)
            if job.finished_at is not None
            else None,
        )


def new_job_query_repository(session: AsyncSession) -> JobQueryRepository:
    """Create a job query repository bound to the active session."""
    return JobQueryRepositoryImpl(session)


def _error_to_entity(error: dict | None) -> JobError | None:
    if error is None:
        return None
    return JobError(
        code=error["code"],
        message=error["message"],
        details=error.get("details") or {},
        retryable=bool(error.get("retryable", False)),
    )
