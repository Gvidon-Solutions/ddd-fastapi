"""SQLModel implementation of the job repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, update
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.file import FileStatus
from app.domain.job import (
    AnyJob,
    Initiator,
    Job,
    JobDeleteNotAllowedError,
    JobDetails,
    JobError,
    JobEvent,
    JobExecutionRecord,
    JobFile,
    JobFileRole,
    JobHasChildrenError,
    JobId,
    JobNotFoundError,
    JobRepository,
    JobSerializationError,
    JobStatus,
    JobSummary,
    get_job_class,
)
from app.infrastructure.sqlmodel.datetime import ensure_datetime_utc
from app.infrastructure.sqlmodel.event.event_dto import EventDTO, JobEventLinkDTO
from app.infrastructure.sqlmodel.file import FileDTO
from app.infrastructure.sqlmodel.job.initiator_dto import InitiatorDTO
from app.infrastructure.sqlmodel.job.job_dto import JobDTO, _error_to_record, _to_record
from app.infrastructure.sqlmodel.job.job_file_dto import JobFileDTO
from app.infrastructure.sqlmodel.job.payload_codec import load_payload


class JobRepositoryImpl(JobRepository):
    """Persist jobs with SQLModel."""

    def __init__(self, session: AsyncSession):
        """Store the active SQLModel session."""
        self.session = session

    async def create(self, job: Job) -> None:
        """Create a new job."""
        initiator_id = await self._get_or_create_initiator(job.initiator)
        self.session.add(JobDTO.from_entity(job, initiator_id=initiator_id))

    async def get(self, job_id: JobId) -> AnyJob:
        """Return a job by ID."""
        job = await self.session.get(JobDTO, job_id)
        if job is None:
            raise JobNotFoundError(str(job_id))
        initiator = await self._get_initiator(job.initiator_id)
        return job.to_entity(initiator)

    async def get_detail(self, job_id: JobId) -> JobDetails:
        """Return job details."""
        job = await self.session.get(JobDTO, job_id)
        if job is None:
            raise JobNotFoundError(str(job_id))
        summary = await self._summary(job)
        files = await self.list_files(job_id)
        events = await self.list_events(job_id)
        return JobDetails(
            id=summary.id,
            type=summary.type,
            version=summary.version,
            name=summary.name,
            status=summary.status,
            initiator=summary.initiator,
            parent_job_id=summary.parent_job_id,
            requested_at=summary.requested_at,
            updated_at=summary.updated_at,
            started_at=summary.started_at,
            finished_at=summary.finished_at,
            input=_load_detail_input(job),
            result=_load_detail_result(job),
            error=_error_to_entity(job.error),
            files=tuple(files),
            events=tuple(events),
        )

    async def get_status(self, job_id: JobId) -> JobStatus:
        """Return only the current job status."""
        status = (
            await self.session.exec(
                select(JobDTO.status).where(col(JobDTO.job_id) == job_id)
            )
        ).first()
        if status is None:
            raise JobNotFoundError(str(job_id))
        return JobStatus(status)

    async def list_by_initiator(self, initiator_external_id: str) -> list[JobSummary]:
        """Return jobs created by an initiator external id."""
        statement = (
            select(JobDTO)
            .join(
                InitiatorDTO,
                col(InitiatorDTO.initiator_id) == col(JobDTO.initiator_id),
            )
            .where(col(InitiatorDTO.external_id) == initiator_external_id)
            .order_by(col(JobDTO.requested_at).desc())
        )
        jobs = (await self.session.exec(statement)).all()
        return [await self._summary(job) for job in jobs]

    async def list_children(self, parent_job_id: JobId) -> list[JobSummary]:
        """Return direct child job summaries."""
        statement = (
            select(JobDTO)
            .where(col(JobDTO.parent_job_id) == parent_job_id)
            .order_by(col(JobDTO.requested_at).asc())
        )
        jobs = (await self.session.exec(statement)).all()
        return [await self._summary(job) for job in jobs]

    async def add_file(self, job_file: JobFile) -> None:
        """Associate a file with a job."""
        self.session.add(FileDTO.from_entity(job_file))
        self.session.add(JobFileDTO.from_entity(job_file))

    async def list_files(
        self,
        job_id: JobId,
        role: JobFileRole | None = None,
    ) -> list[JobFile]:
        """Return files associated with a job."""
        statement = (
            select(JobFileDTO, FileDTO)
            .join(FileDTO, col(FileDTO.file_id) == col(JobFileDTO.file_id))
            .where(col(JobFileDTO.job_id) == job_id)
            .order_by(col(JobFileDTO.created_at).asc())
        )
        if role is not None:
            statement = statement.where(col(JobFileDTO.role) == role.value)
        rows = (await self.session.exec(statement)).all()
        return [job_file.to_entity(file) for job_file, file in rows]

    async def append_event(self, job_id: JobId, event: JobEvent) -> None:
        """Append a new job event."""
        self.session.add(EventDTO.from_job_event(event))
        sequence = await self._next_event_sequence(job_id)
        self.session.add(
            JobEventLinkDTO(
                job_id=job_id,
                event_id=event.event_id,
                relation="emitted",
                sequence=sequence,
                created_at=event.created_at,
            )
        )

    async def list_events(self, job_id: JobId) -> list[JobEvent]:
        """Return events emitted by a job."""
        statement = (
            select(EventDTO, JobEventLinkDTO)
            .join(
                JobEventLinkDTO,
                col(JobEventLinkDTO.event_id) == col(EventDTO.event_id),
            )
            .where(col(JobEventLinkDTO.job_id) == job_id)
            .order_by(col(JobEventLinkDTO.sequence).asc())
        )
        result = await self.session.exec(statement)
        return [event.to_entity(job_id=JobId(link.job_id)) for event, link in result.all()]

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
        existing_job.dispatch_attempts = job_dto.dispatch_attempts
        existing_job.next_dispatch_at = job_dto.next_dispatch_at
        existing_job.last_dispatch_error = job_dto.last_dispatch_error
        existing_job.dispatched_at = job_dto.dispatched_at
        self.session.add(existing_job)

    async def _get_or_create_initiator(self, initiator: Initiator):
        if initiator.external_id is not None:
            statement = select(InitiatorDTO).where(
                col(InitiatorDTO.type) == initiator.type.value,
                col(InitiatorDTO.external_id) == initiator.external_id,
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

    async def _summary(self, job: JobDTO) -> JobSummary:
        initiator = await self.session.get(InitiatorDTO, job.initiator_id)
        if initiator is None:
            raise KeyError(str(job.initiator_id))
        return JobSummary(
            id=JobId(job.job_id),
            type=job.type,
            version=job.version,
            name=job.name,
            status=JobStatus(job.status),
            initiator=initiator.to_value_object(),
            parent_job_id=JobId(job.parent_job_id)
            if job.parent_job_id is not None
            else None,
            requested_at=ensure_datetime_utc(job.requested_at),
            updated_at=ensure_datetime_utc(job.updated_at),
            started_at=ensure_datetime_utc(job.started_at)
            if job.started_at is not None
            else None,
            finished_at=ensure_datetime_utc(job.finished_at)
            if job.finished_at is not None
            else None,
        )

    async def _next_event_sequence(self, job_id: JobId) -> int:
        statement = select(func.max(JobEventLinkDTO.sequence)).where(
            col(JobEventLinkDTO.job_id) == job_id
        )
        result = await self.session.exec(statement)
        return (result.one() or 0) + 1

    async def get_execution_record(self, job_id: JobId) -> JobExecutionRecord:
        """Return raw execution data without typed deserialization."""
        job = await self.session.get(JobDTO, job_id)
        if job is None:
            raise JobNotFoundError(str(job_id))
        return JobExecutionRecord(
            job_id=JobId(job.job_id),
            type=job.type,
            version=job.version,
            input=job.input,
            status=JobStatus(job.status),
        )

    async def try_mark_running(
        self,
        job_id: JobId,
        *,
        started_at: datetime,
    ) -> bool:
        """Atomically mark an enqueued job as running."""
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
        job_id: JobId,
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
        job_id: JobId,
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
        job_id: JobId,
        *,
        error: JobError,
        finished_at: datetime,
    ) -> bool:
        """Atomically mark a pending, queued, or running job as cancelled."""
        statement = (
            update(JobDTO)
            .where(
                col(JobDTO.job_id) == job_id,
                col(JobDTO.status).in_(
                    [
                        JobStatus.PENDING.value,
                        JobStatus.QUEUED.value,
                        JobStatus.RUNNING.value,
                    ]
                ),
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
        job_id: JobId,
        *,
        expected: JobStatus,
        values: dict,
    ) -> bool:
        statement = (
            update(JobDTO)
            .where(
                col(JobDTO.job_id) == job_id,
                col(JobDTO.status) == expected.value,
            )
            .values(**values)
        )
        result = await self.session.exec(statement)
        return (result.rowcount or 0) == 1

    async def delete(self, job_id: JobId, *, cascade_children: bool = False) -> None:
        """Delete a terminal job and clean up links/orphan metadata."""
        job = await self.session.get(JobDTO, job_id)
        if job is None:
            raise JobNotFoundError(str(job_id))
        if JobStatus(job.status) not in _TERMINAL_STATUSES:
            raise JobDeleteNotAllowedError(str(job_id))

        child_ids = (
            await self.session.exec(
                select(JobDTO.job_id).where(col(JobDTO.parent_job_id) == job_id)
            )
        ).all()
        if child_ids and not cascade_children:
            raise JobHasChildrenError(str(job_id))
        for child_id in child_ids:
            await self.delete(JobId(child_id), cascade_children=True)

        await self._delete_job_file_links(job_id)
        await self._delete_job_event_links(job_id)
        await self.session.exec(delete(JobDTO).where(col(JobDTO.job_id) == job_id))

    async def _delete_job_file_links(self, job_id: JobId) -> None:
        file_ids = (
            await self.session.exec(
                select(JobFileDTO.file_id).where(col(JobFileDTO.job_id) == job_id)
            )
        ).all()
        await self.session.exec(
            delete(JobFileDTO).where(col(JobFileDTO.job_id) == job_id)
        )
        now = datetime.now(UTC)
        for file_id in file_ids:
            remaining_links = await self._job_file_link_count(file_id)
            if remaining_links == 0:
                await self.session.exec(
                    update(FileDTO)
                    .where(col(FileDTO.file_id) == file_id)
                    .values(
                        status=FileStatus.PENDING_DELETE.value,
                        delete_requested_at=now,
                    )
                )

    async def _delete_job_event_links(self, job_id: JobId) -> None:
        event_ids = (
            await self.session.exec(
                select(JobEventLinkDTO.event_id).where(
                    col(JobEventLinkDTO.job_id) == job_id
                )
            )
        ).all()
        await self.session.exec(
            delete(JobEventLinkDTO).where(col(JobEventLinkDTO.job_id) == job_id)
        )
        for event_id in event_ids:
            remaining_links = await self._job_event_link_count(event_id)
            if remaining_links == 0:
                await self.session.exec(
                    delete(EventDTO).where(col(EventDTO.event_id) == event_id)
                )

    async def _job_file_link_count(self, file_id: UUID) -> int:
        result = await self.session.exec(
            select(func.count()).select_from(JobFileDTO).where(
                col(JobFileDTO.file_id) == file_id
            )
        )
        return int(result.one())

    async def _job_event_link_count(self, event_id: UUID) -> int:
        result = await self.session.exec(
            select(func.count()).select_from(JobEventLinkDTO).where(
                col(JobEventLinkDTO.event_id) == event_id
            )
        )
        return int(result.one())


def new_job_repository(session: AsyncSession) -> JobRepository:
    """Create a job repository bound to the active session."""
    return JobRepositoryImpl(session)


def _error_to_entity(error: dict | None) -> JobError | None:
    if error is None:
        return None
    return JobError(
        code=error["code"],
        message=error["message"],
        details=error.get("details") or {},
        retryable=bool(error.get("retryable", False)),
    )


def _load_detail_input(job: JobDTO) -> object:
    contract = get_job_class(type=job.type, version=job.version)
    if contract is None:
        return job.input
    try:
        return load_payload(job.input, _payload_type(contract, "input"))
    except JobSerializationError:
        return job.input


def _load_detail_result(job: JobDTO) -> object | None:
    if job.result is None:
        return None
    contract = get_job_class(type=job.type, version=job.version)
    if contract is None:
        return job.result
    try:
        return load_payload(job.result, _payload_type(contract, "result"))
    except JobSerializationError:
        return job.result


def _payload_type(job_class: type[Job], field_name: str) -> type:
    payload_type = getattr(job_class, field_name, None)
    if not isinstance(payload_type, type):
        raise JobSerializationError(
            f"Job {job_class.__name__} must define {field_name} payload type"
        )
    return payload_type


_TERMINAL_STATUSES = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
