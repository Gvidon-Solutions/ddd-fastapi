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
    JobEventPayload,
    JobEventType,
    JobStage,
    JobStatus,
)
from app.domain.job.codex_auth_job_use_case import (
    CodexAuthJobResult,
    Event3CodexAuthSucceeded,
    Event3CodexAuthSucceededPayload,
)
from app.infrastructure.sqlmodel.event import EventDTO
from app.infrastructure.sqlmodel.job import JobArtifactDTO, JobDTO


def test_job_dto_round_trips_entity_fields() -> None:
    # Arrange
    stage_updated_at = datetime(2026, 6, 23, 0, 30, tzinfo=UTC)
    job = Job(
        job_id=uuid4(),
        job_type="codex_run",
        job_name="Run Codex",
        job_description="Run Codex against repository",
        job_input={"prompt": "Review repository"},
        job_status=JobStatus.RUNNING,
        job_stage=JobStage(
            key="running_codex",
            current=1,
            total=2,
            message="Running",
            updated_at=stage_updated_at,
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
        updated_at=datetime(2026, 6, 23, 0, 30, tzinfo=UTC),
        started_at=datetime(2026, 6, 23, 1, tzinfo=UTC),
        finished_at=None,
        job_error=JobError(
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
        artifact_id=uuid4(),
        job_id=uuid4(),
        name="report.txt",
        description=None,
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


def test_event_dto_round_trips_job_event_fields() -> None:
    # Arrange
    event = JobEvent(
        event_id=uuid4(),
        type="JobArtifactCreatedV1",
        source="job",
        version="v1",
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        payload=JobEventPayload(
            job_id_issuer=uuid4(),
            job_event_type=JobEventType.ARTIFACT_CREATED,
            message="Created artifact",
        ),
    )

    # Act
    entity = EventDTO.from_job_event(event).to_job_event()

    # Assert
    assert entity == event


def test_event_dto_casts_to_typed_event_dataclass() -> None:
    # Arrange
    result = CodexAuthJobResult(
        authenticated=True,
        verification_url="https://auth.openai.com/device",
        device_code="ABCD-EFGH",
    )
    event = Event3CodexAuthSucceeded(
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        payload=Event3CodexAuthSucceededPayload(
            job_id_issuer=uuid4(),
            summary=result,
        ),
    )

    # Act
    entity = EventDTO.from_job_event(event).to_entity()

    # Assert
    assert isinstance(entity, Event3CodexAuthSucceeded)
    assert isinstance(entity.payload, Event3CodexAuthSucceededPayload)
    assert entity.payload.summary == result
    assert entity == event
