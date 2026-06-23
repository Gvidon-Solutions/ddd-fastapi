"""Job SQLModel repository tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.job import (
    Actor,
    ActorType,
    ArtifactKind,
    ArtifactLocation,
    ArtifactLocationType,
    ArtifactRole,
    Job,
    JobArtifact,
    JobError,
    JobEvent,
    JobEventType,
    JobStage,
    JobStatus,
)
from app.infrastructure.sqlmodel.job import (
    new_job_artifact_repository,
    new_job_event_repository,
    new_job_repository,
)

pytestmark = pytest.mark.anyio


def _job(name: str = "run_codex") -> Job:
    return Job(
        id=uuid4(),
        name=name,
        input={"prompt": "Review repository"},
        status=JobStatus.QUEUED,
        stage=None,
        result_summary=None,
        root_initiator=Actor(type=ActorType.USER, id="anton"),
        parent_job_id=None,
        requested_at=datetime(2026, 6, 23, tzinfo=UTC),
        started_at=None,
        finished_at=None,
        error=None,
    )


async def test_job_repository_creates_and_gets_job(db_session) -> None:
    # Arrange
    repository = new_job_repository(db_session)
    job = _job()

    # Act
    await repository.create(job)
    await db_session.commit()

    # Assert
    assert await repository.get(job.id) == job


async def test_job_repository_saves_job_changes(db_session) -> None:
    # Arrange
    repository = new_job_repository(db_session)
    job = _job()
    await repository.create(job)
    await db_session.commit()
    job.status = JobStatus.FAILED
    job.stage = JobStage(key="failed", data={"retryable": False})
    job.error = JobError(code="RuntimeError", message="failed")
    job.finished_at = datetime(2026, 6, 23, 1, tzinfo=UTC)

    # Act
    await repository.save(job)
    await db_session.commit()

    # Assert
    assert await repository.get(job.id) == job


async def test_job_artifact_repository_lists_and_filters_artifacts(db_session) -> None:
    # Arrange
    job_repository = new_job_repository(db_session)
    artifact_repository = new_job_artifact_repository(db_session)
    job = _job()
    await job_repository.create(job)
    output = JobArtifact(
        id=uuid4(),
        job_id=job.id,
        role=ArtifactRole.OUTPUT,
        kind=ArtifactKind.FILE,
        location=ArtifactLocation(
            type=ArtifactLocationType.FILESYSTEM,
            uri="/tmp/output.txt",
        ),
        metadata={"filename": "output.txt"},
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
    )
    log = JobArtifact(
        id=uuid4(),
        job_id=job.id,
        role=ArtifactRole.LOG,
        kind=ArtifactKind.TEXT,
        location=ArtifactLocation(
            type=ArtifactLocationType.FILESYSTEM,
            uri="/tmp/stdout.log",
        ),
        metadata={"filename": "stdout.log"},
        created_at=datetime(2026, 6, 23, 1, tzinfo=UTC),
    )
    await artifact_repository.create(output)
    await artifact_repository.create(log)
    await db_session.commit()

    # Act
    outputs = await artifact_repository.list_by_job(job.id, role=ArtifactRole.OUTPUT)
    artifacts = await artifact_repository.list_by_job(job.id)

    # Assert
    assert outputs == [output]
    assert artifacts == [output, log]


async def test_job_event_repository_appends_and_lists_events(db_session) -> None:
    # Arrange
    job_repository = new_job_repository(db_session)
    event_repository = new_job_event_repository(db_session)
    job = _job()
    await job_repository.create(job)
    started = JobEvent(
        id=uuid4(),
        job_id=job.id,
        type=JobEventType.STARTED,
        data={},
        message=None,
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
    )
    succeeded = JobEvent(
        id=uuid4(),
        job_id=job.id,
        type=JobEventType.SUCCEEDED,
        data={"summary": {"changed_files": 1}},
        message=None,
        created_at=datetime(2026, 6, 23, 1, tzinfo=UTC),
    )

    # Act
    await event_repository.append(started)
    await event_repository.append(succeeded)
    await db_session.commit()

    # Assert
    assert await event_repository.list_by_job(job.id) == [started, succeeded]
