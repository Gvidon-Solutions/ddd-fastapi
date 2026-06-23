"""Job domain tests."""

from datetime import UTC, datetime
from uuid import uuid4

from app.domain.job import (
    Actor,
    ActorType,
    ArtifactKind,
    ArtifactLocation,
    ArtifactLocationType,
    ArtifactRole,
    Job,
    JobArtifact,
    JobEvent,
    JobEventType,
    JobStatus,
)


def test_job_represents_a_queued_execution() -> None:
    # Arrange
    now = datetime(2026, 6, 23, tzinfo=UTC)
    initiator = Actor(
        type=ActorType.USER,
        id="anton",
        display_name="Anton",
    )

    # Act
    job = Job(
        id=uuid4(),
        name="run_codex",
        input={"prompt": "Review repository"},
        status=JobStatus.QUEUED,
        stage=None,
        result_summary=None,
        root_initiator=initiator,
        parent_job_id=None,
        requested_at=now,
        started_at=None,
        finished_at=None,
        error=None,
    )

    # Assert
    assert job.name == "run_codex"
    assert job.input == {"prompt": "Review repository"}
    assert job.status == JobStatus.QUEUED
    assert job.root_initiator == initiator


def test_job_artifact_and_event_capture_execution_output() -> None:
    # Arrange
    now = datetime(2026, 6, 23, tzinfo=UTC)
    job_id = uuid4()

    # Act
    artifact = JobArtifact(
        id=uuid4(),
        job_id=job_id,
        role=ArtifactRole.OUTPUT,
        kind=ArtifactKind.FILE,
        location=ArtifactLocation(
            type=ArtifactLocationType.FILESYSTEM,
            uri="/tmp/jobs/changed.py",
        ),
        metadata={"filename": "changed.py", "source": "codex"},
        created_at=now,
    )
    event = JobEvent(
        id=uuid4(),
        job_id=job_id,
        type=JobEventType.ARTIFACT_CREATED,
        data={"artifact_id": str(artifact.id)},
        message="Created artifact changed.py",
        created_at=now,
    )

    # Assert
    assert artifact.job_id == job_id
    assert artifact.role == ArtifactRole.OUTPUT
    assert event.type == JobEventType.ARTIFACT_CREATED
    assert event.data == {"artifact_id": str(artifact.id)}
