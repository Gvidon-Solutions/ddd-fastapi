"""Job SQLModel DTO tests."""

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
    JobError,
    JobEvent,
    JobEventType,
    JobStage,
    JobStatus,
)
from app.infrastructure.sqlmodel.job import JobArtifactDTO, JobDTO, JobEventDTO


def test_job_dto_round_trips_entity_fields() -> None:
    # Arrange
    job = Job(
        id=uuid4(),
        name="run_codex",
        input={"prompt": "Review repository"},
        status=JobStatus.RUNNING,
        stage=JobStage(
            key="running_codex",
            current=1,
            total=2,
            message="Running",
            data={"pid": 123},
        ),
        result_summary={"changed_files": 2},
        root_initiator=Actor(
            type=ActorType.USER,
            id="anton",
            display_name="Anton",
        ),
        parent_job_id=None,
        requested_at=datetime(2026, 6, 23, tzinfo=UTC),
        started_at=datetime(2026, 6, 23, 1, tzinfo=UTC),
        finished_at=None,
        error=JobError(
            code="RuntimeError",
            message="failed",
            details={"step": "codex"},
        ),
    )

    # Act
    entity = JobDTO.from_entity(job).to_entity()

    # Assert
    assert entity == job


def test_job_artifact_dto_round_trips_entity_fields() -> None:
    # Arrange
    artifact = JobArtifact(
        id=uuid4(),
        job_id=uuid4(),
        role=ArtifactRole.OUTPUT,
        kind=ArtifactKind.FILE,
        location=ArtifactLocation(
            type=ArtifactLocationType.FILESYSTEM,
            uri="/tmp/report.txt",
        ),
        metadata={"filename": "report.txt"},
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
    )

    # Act
    entity = JobArtifactDTO.from_entity(artifact).to_entity()

    # Assert
    assert entity == artifact


def test_job_event_dto_round_trips_entity_fields() -> None:
    # Arrange
    event = JobEvent(
        id=uuid4(),
        job_id=uuid4(),
        type=JobEventType.ARTIFACT_CREATED,
        data={"artifact_id": str(uuid4())},
        message="Created artifact",
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
    )

    # Act
    entity = JobEventDTO.from_entity(event).to_entity()

    # Assert
    assert entity == event
