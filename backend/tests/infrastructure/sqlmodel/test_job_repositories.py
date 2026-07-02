"""Job SQLModel repository tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.job import (
    ActorType,
    File,
    FileKind,
    FileLocation,
    FileLocationType,
    FileStatus,
    Initiator,
    Job,
    JobError,
    JobEvent,
    JobEventPayload,
    JobFile,
    JobFileRole,
    JobStatus,
)
from app.domain.job.codex_auth_job_use_case import CodexAuthInputV1
from app.infrastructure.sqlmodel.event import new_job_event_repository
from app.infrastructure.sqlmodel.job import (
    new_job_file_repository,
    new_job_query_repository,
    new_job_repository,
)

pytestmark = pytest.mark.anyio


def _job() -> Job:
    return Job(
        id=uuid4(),
        type="codex.auth",
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
        file_id=uuid4(),
        name=name,
        kind=FileKind.FILE,
        location=FileLocation(
            type=FileLocationType.FILESYSTEM,
            uri=f"/tmp/{name}",
        ),
        metadata={"filename": name},
        status=FileStatus.ACTIVE,
        delete_requested_at=None,
        delete_attempts=0,
        last_delete_error=None,
        created_at=created_at,
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


async def test_job_file_repository_lists_and_filters_files(db_session) -> None:
    job_repository = new_job_repository(db_session)
    file_repository = new_job_file_repository(db_session)
    job = _job()
    await job_repository.create(job)
    output = JobFile(
        job_id=job.id,
        file=_file("output.txt", created_at=datetime(2026, 6, 23, tzinfo=UTC)),
        role=JobFileRole.OUTPUT,
        description=None,
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
    )
    log = JobFile(
        job_id=job.id,
        file=_file("stdout.log", created_at=datetime(2026, 6, 23, 1, tzinfo=UTC)),
        role=JobFileRole.LOG,
        description=None,
        created_at=datetime(2026, 6, 23, 1, tzinfo=UTC),
    )
    await file_repository.create(output)
    await file_repository.create(log)
    await db_session.commit()

    outputs = await file_repository.list_by_job(job.id, role=JobFileRole.OUTPUT)
    files = await file_repository.list_by_job(job.id)

    assert outputs == [output]
    assert files == [output, log]


async def test_job_event_repository_appends_and_lists_events(db_session) -> None:
    job_repository = new_job_repository(db_session)
    event_repository = new_job_event_repository(db_session)
    job = _job()
    await job_repository.create(job)
    started = JobEvent(
        event_id=uuid4(),
        type="JobStartedV1",
        source="job",
        version="v1",
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        payload=JobEventPayload(),
    )
    succeeded = JobEvent(
        event_id=uuid4(),
        type="JobSucceededV1",
        source="job",
        version="v1",
        created_at=datetime(2026, 6, 23, 1, tzinfo=UTC),
        payload=JobEventPayload(),
    )

    await event_repository.append(job.id, started)
    await event_repository.append(job.id, succeeded)
    await db_session.commit()

    assert await event_repository.list_by_job(job.id) == [started, succeeded]


async def test_job_query_repository_reads_detail_without_contract_get(db_session) -> None:
    job_repository = new_job_repository(db_session)
    query_repository = new_job_query_repository(db_session)
    job = _job()
    await job_repository.create(job)
    await db_session.commit()

    detail = await query_repository.get_detail(job.id)

    assert detail.summary.id == job.id
    assert detail.summary.initiator.external_id == "anton"
    assert detail.input == {}
