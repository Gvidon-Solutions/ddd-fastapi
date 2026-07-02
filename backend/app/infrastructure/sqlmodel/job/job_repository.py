"""SQLModel implementation of the job repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import (
    AnyJob,
    FileStatus,
    Initiator,
    Job,
    JobDeleteNotAllowedError,
    JobError,
    JobExecutionRecord,
    JobHasChildrenError,
    JobRepository,
    JobStatus,
)
from app.infrastructure.sqlmodel.event.event_dto import EventDTO, JobEventLinkDTO
from app.infrastructure.sqlmodel.job.file_dto import FileDTO
from app.infrastructure.sqlmodel.job.initiator_dto import InitiatorDTO
from app.infrastructure.sqlmodel.job.job_dispatch_outbox_dto import JobDispatchOutboxDTO
from app.infrastructure.sqlmodel.job.job_dto import JobDTO, _error_to_record, _to_record
from app.infrastructure.sqlmodel.job.job_file_dto import JobFileDTO


class JobRepositoryImpl(JobRepository):
    """Persist jobs with SQLModel."""

    def __init__(self, session: AsyncSession):
        """Store the active SQLModel session."""
        self.session = session

    async def create(self, job: Job) -> None:
        """Create a new job."""
        initiator_id = await self._get_or_create_initiator(job.initiator)
        self.session.add(JobDTO.from_entity(job, initiator_id=initiator_id))

    async def get(self, job_id: UUID) -> AnyJob:
        """Return a job by ID."""
        job = await self.session.get(JobDTO, job_id)
        if job is None:
            raise KeyError(str(job_id))
        initiator = await self._get_initiator(job.initiator_id)
        return job.to_entity(initiator)

    async def save(self, job: Job) -> None:
        """Persist metadata changes to an existing job."""
        initiator_id = await self._get_or_create_initiator(job.initiator)
        job_dto = JobDTO.from_entity(job, initiator_id=initiator_id)
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
        existing_job.initiator_id = job_dto.initiator_id
        existing_job.parent_job_id = job_dto.parent_job_id
        existing_job.requested_at = job_dto.requested_at
        existing_job.updated_at = job_dto.updated_at
        existing_job.started_at = job_dto.started_at
        existing_job.finished_at = job_dto.finished_at
        existing_job.error = job_dto.error
        self.session.add(existing_job)

    async def _get_or_create_initiator(self, initiator: Initiator):
        if initiator.external_id is not None:
            statement = select(InitiatorDTO).where(
                InitiatorDTO.type == initiator.type.value,
                InitiatorDTO.external_id == initiator.external_id,
            )
            existing = (await self.session.exec(statement)).first()
            if existing is not None:
                return existing.initiator_id

        dto = InitiatorDTO(
            type=initiator.type.value,
            external_id=initiator.external_id,
            display_name=initiator.display_name,
            initiator_metadata=initiator.metadata or {},
        )
        self.session.add(dto)
        await self.session.flush()
        return dto.initiator_id

    async def _get_initiator(self, initiator_id) -> Initiator:
        initiator = await self.session.get(InitiatorDTO, initiator_id)
        if initiator is None:
            raise KeyError(str(initiator_id))
        return initiator.to_value_object()

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

    async def delete(self, job_id: UUID, *, cascade_children: bool = False) -> None:
        """Delete a terminal job and clean up links/orphan metadata."""
        job = await self.session.get(JobDTO, job_id)
        if job is None:
            raise KeyError(str(job_id))
        if JobStatus(job.status) not in _TERMINAL_STATUSES:
            raise JobDeleteNotAllowedError(str(job_id))

        child_ids = (
            await self.session.exec(
                select(JobDTO.job_id).where(JobDTO.parent_job_id == job_id)
            )
        ).all()
        if child_ids and not cascade_children:
            raise JobHasChildrenError(str(job_id))
        for child_id in child_ids:
            await self.delete(child_id, cascade_children=True)

        await self._delete_job_file_links(job_id)
        await self._delete_job_event_links(job_id)
        await self.session.exec(
            delete(JobDispatchOutboxDTO).where(JobDispatchOutboxDTO.job_id == job_id)
        )
        await self.session.exec(delete(JobDTO).where(JobDTO.job_id == job_id))

    async def _delete_job_file_links(self, job_id: UUID) -> None:
        file_ids = (
            await self.session.exec(
                select(JobFileDTO.file_id).where(JobFileDTO.job_id == job_id)
            )
        ).all()
        await self.session.exec(delete(JobFileDTO).where(JobFileDTO.job_id == job_id))
        now = datetime.now(UTC)
        for file_id in file_ids:
            remaining_links = await self._job_file_link_count(file_id)
            if remaining_links == 0:
                await self.session.exec(
                    update(FileDTO)
                    .where(FileDTO.file_id == file_id)
                    .values(
                        status=FileStatus.PENDING_DELETE.value,
                        delete_requested_at=now,
                    )
                )

    async def _delete_job_event_links(self, job_id: UUID) -> None:
        event_ids = (
            await self.session.exec(
                select(JobEventLinkDTO.event_id).where(JobEventLinkDTO.job_id == job_id)
            )
        ).all()
        await self.session.exec(
            delete(JobEventLinkDTO).where(JobEventLinkDTO.job_id == job_id)
        )
        for event_id in event_ids:
            remaining_links = await self._job_event_link_count(event_id)
            if remaining_links == 0:
                await self.session.exec(
                    delete(EventDTO).where(EventDTO.event_id == event_id)
                )

    async def _job_file_link_count(self, file_id: UUID) -> int:
        result = await self.session.exec(
            select(func.count()).select_from(JobFileDTO).where(
                JobFileDTO.file_id == file_id
            )
        )
        return int(result.one())

    async def _job_event_link_count(self, event_id: UUID) -> int:
        result = await self.session.exec(
            select(func.count()).select_from(JobEventLinkDTO).where(
                JobEventLinkDTO.event_id == event_id
            )
        )
        return int(result.one())


def new_job_repository(session: AsyncSession) -> JobRepository:
    """Create a job repository bound to the active session."""
    return JobRepositoryImpl(session)


_TERMINAL_STATUSES = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
