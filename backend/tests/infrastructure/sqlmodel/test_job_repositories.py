"""Job SQLModel repository tests."""

from datetime import UTC, datetime

import pytest

from app.domain.event import new_event_id
from app.domain.file import File, FileKind, FileLocation, FileStatus, new_file_id
from app.domain.job import (
    ActorType,
    Initiator,
    Job,
    JobError,
    JobEvent,
    JobEventPayload,
    JobFile,
    JobFileRole,
    JobId,
    JobStatus,
    new_job_id,
)
from app.domain.job.codex_auth_job_use_case import (
    CodexAuthInputV1,
    CodexAuthJobV1,
    CodexAuthResult,
    Event3CodexAuthSucceeded,
    Event3CodexAuthSucceededPayload,
)
from app.infrastructure.sqlmodel.job import new_job_repository

pytestmark = pytest.mark.anyio


def _job() -> Job:
    return CodexAuthJobV1(
        id=new_job_id(),
        type="execute_codex_auth_job_use_case",
        version="v1",
        name="Codex auth",
        description=None,
        input=CodexAuthInputV1(),
        result=None,
        status=JobStatus.QUEUED,
        initiator=Initiator(type=ActorType.USER, external_id="anton"),
        parent_job_id=None,
        requested_at=datetime(2026, 6, 23, tzinfo=UTC),
        updated_at=datetime(2026, 6, 23, tzinfo=UTC),
        started_at=None,
        finished_at=None,
        error=None,
    )


def _file(name: str, *, created_at: datetime) -> File:
    return File(
        file_id=new_file_id(),
        name=name,
        kind=FileKind.FILE,
        location=FileLocation(
            uri=f"file:///tmp/{name}",
        ),
        metadata={"filename": name},
        status=FileStatus.ACTIVE,
        delete_requested_at=None,
        delete_attempts=0,
        last_delete_error=None,
        created_at=created_at,
    )


def _job_file(
    *,
    job_id: JobId,
    file: File,
    role: JobFileRole,
) -> JobFile:
    return JobFile(
        file_id=file.file_id,
        name=file.name,
        kind=file.kind,
        location=file.location,
        metadata=file.metadata,
        status=file.status,
        delete_requested_at=file.delete_requested_at,
        delete_attempts=file.delete_attempts,
        last_delete_error=file.last_delete_error,
        created_at=file.created_at,
        job_id=job_id,
        role=role,
        description=None,
        attached_at=file.created_at,
    )


async def test_job_repository_creates_and_gets_job(db_session) -> None:
    repository = new_job_repository(db_session)
    job = _job()

    await repository.create(job)
    await db_session.commit()

    assert await repository.get(job.id) == job


async def test_job_repository_saves_job_changes(db_session) -> None:
    repository = new_job_repository(db_session)
    job = _job()
    await repository.create(job)
    await db_session.commit()
    job.status = JobStatus.FAILED
    job.updated_at = datetime(2026, 6, 23, 1, tzinfo=UTC)
    job.error = JobError(code="RuntimeError", message="failed")
    job.finished_at = datetime(2026, 6, 23, 1, tzinfo=UTC)

    await repository.save(job)
    await db_session.commit()

    assert await repository.get(job.id) == job


async def test_job_repository_lists_and_filters_files(db_session) -> None:
    job_repository = new_job_repository(db_session)
    job = _job()
    await job_repository.create(job)
    output = _job_file(
        job_id=job.id,
        file=_file("output.txt", created_at=datetime(2026, 6, 23, tzinfo=UTC)),
        role=JobFileRole.OUTPUT,
    )
    log = _job_file(
        job_id=job.id,
        file=_file("stdout.log", created_at=datetime(2026, 6, 23, 1, tzinfo=UTC)),
        role=JobFileRole.LOG,
    )
    await job_repository.add_file(output)
    await job_repository.add_file(log)
    await db_session.commit()

    outputs = await job_repository.list_files(job.id, role=JobFileRole.OUTPUT)
    files = await job_repository.list_files(job.id)

    assert outputs == [output]
    assert files == [output, log]


async def test_job_repository_appends_and_lists_events(db_session) -> None:
    job_repository = new_job_repository(db_session)
    job = _job()
    await job_repository.create(job)
    started = JobEvent(
        event_id=new_event_id(),
        type="JobStartedV1",
        source="job",
        version="v1",
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        payload=JobEventPayload(job_id=job.id),
    )
    succeeded = JobEvent(
        event_id=new_event_id(),
        type="JobSucceededV1",
        source="job",
        version="v1",
        created_at=datetime(2026, 6, 23, 1, tzinfo=UTC),
        payload=JobEventPayload(job_id=job.id),
    )

    await job_repository.append_event(job.id, started)
    await job_repository.append_event(job.id, succeeded)
    await db_session.commit()

    assert await job_repository.list_events(job.id) == [started, succeeded]


async def test_job_repository_lists_typed_events(db_session) -> None:
    job_repository = new_job_repository(db_session)
    job = _job()
    await job_repository.create(job)
    event = Event3CodexAuthSucceeded(
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        payload=Event3CodexAuthSucceededPayload(
            job_id=job.id,
            summary=CodexAuthResult(authenticated=True),
        ),
    )

    await job_repository.append_event(job.id, event)
    await db_session.commit()

    events = await job_repository.list_events(job.id)

    assert events == [event]
    assert isinstance(events[0], Event3CodexAuthSucceeded)
    assert isinstance(events[0].payload, Event3CodexAuthSucceededPayload)


async def test_job_repository_reads_typed_detail_without_contract_get(db_session) -> None:
    job_repository = new_job_repository(db_session)
    job = _job()
    await job_repository.create(job)
    await db_session.commit()

    detail = await job_repository.get_detail(job.id)

    assert detail.id == job.id
    assert detail.initiator.external_id == "anton"
    assert type(detail.input) is CodexAuthInputV1
