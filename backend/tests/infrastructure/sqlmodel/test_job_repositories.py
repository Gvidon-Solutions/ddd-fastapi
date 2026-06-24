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
    JobEventPayload,
    JobEventType,
    JobStage,
    JobStatus,
)
from app.infrastructure.sqlmodel.event import new_job_event_repository
from app.infrastructure.sqlmodel.job import (
    new_job_artifact_repository,
    new_job_repository,
)

pytestmark = pytest.mark.anyio


def _job(
    job_type: str = "codex_run",
    job_name: str = "Run Codex",
) -> Job:
    return Job(
        job_id=uuid4(),
        job_type=job_type,
        job_name=job_name,
        job_description=None,
        job_input={"prompt": "Review repository"},
        job_status=JobStatus.QUEUED,
        job_stage=None,
        result_summary=None,
        root_initiator=Actor(type=ActorType.USER, id="anton"),
        parent_job_id=None,
        requested_at=datetime(2026, 6, 23, tzinfo=UTC),
        updated_at=datetime(2026, 6, 23, tzinfo=UTC),
        started_at=None,
        finished_at=None,
        job_error=None,
    )


async def test_job_repository_creates_and_gets_job(db_session) -> None:
    # Arrange
    repository = new_job_repository(db_session)
    job = _job()

    # Act
    await repository.create(job)
    await db_session.commit()

    # Assert
    assert await repository.get(job.job_id) == job


async def test_job_repository_saves_job_changes(db_session) -> None:
    # Arrange
    repository = new_job_repository(db_session)
    job = _job()
    await repository.create(job)
    await db_session.commit()
    job.job_status = JobStatus.FAILED
    job.updated_at = datetime(2026, 6, 23, 1, tzinfo=UTC)
    job.job_stage = JobStage(
        key="failed",
        updated_at=job.updated_at,
        data={"retryable": False},
    )
    job.job_error = JobError(code="RuntimeError", message="failed")
    job.finished_at = datetime(2026, 6, 23, 1, tzinfo=UTC)

    # Act
    await repository.save(job)
    await db_session.commit()

    # Assert
    assert await repository.get(job.job_id) == job


async def test_job_artifact_repository_lists_and_filters_artifacts(db_session) -> None:
    # Arrange
    job_repository = new_job_repository(db_session)
    artifact_repository = new_job_artifact_repository(db_session)
    job = _job()
    await job_repository.create(job)
    output = JobArtifact(
        artifact_id=uuid4(),
        job_id=job.job_id,
        name="output.txt",
        description=None,
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
        artifact_id=uuid4(),
        job_id=job.job_id,
        name="stdout.log",
        description=None,
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
    outputs = await artifact_repository.list_by_job(job.job_id, role=ArtifactRole.OUTPUT)
    artifacts = await artifact_repository.list_by_job(job.job_id)

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
        event_id=uuid4(),
        type="JobStartedV1",
        source="job",
        version="v1",
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        payload=JobEventPayload(
            job_id_issuer=job.job_id,
            job_event_type=JobEventType.STARTED,
            message=None,
        ),
    )
    succeeded = JobEvent(
        event_id=uuid4(),
        type="JobSucceededV1",
        source="job",
        version="v1",
        created_at=datetime(2026, 6, 23, 1, tzinfo=UTC),
        payload=JobEventPayload(
            job_id_issuer=job.job_id,
            job_event_type=JobEventType.SUCCEEDED,
            message=None,
        ),
    )

    # Act
    await event_repository.append(started)
    await event_repository.append(succeeded)
    await db_session.commit()

    # Assert
    assert await event_repository.list_by_job(job.job_id) == [started, succeeded]
