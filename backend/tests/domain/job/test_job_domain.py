"""Job domain tests."""

from dataclasses import dataclass, field
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
    JobEventPayload,
    JobEventType,
    JobStatus,
)


@dataclass(kw_only=True)
class JobArtifactCreatedPayload(JobEventPayload):
    """Represent a job artifact created payload."""

    job_event_type: JobEventType = field(
        default=JobEventType.ARTIFACT_CREATED,
        init=False,
    )
    message: str | None = field(default="Created artifact changed.py", init=False)
    artifact_id: str


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
        job_id=uuid4(),
        job_type="codex_run",
        job_name="Run Codex",
        job_description="Run Codex against repository",
        job_input={"prompt": "Review repository"},
        job_status=JobStatus.QUEUED,
        job_stage=None,
        result_summary=None,
        root_initiator=initiator,
        parent_job_id=None,
        requested_at=now,
        updated_at=now,
        started_at=None,
        finished_at=None,
        job_error=None,
    )

    # Assert
    assert job.job_type == "codex_run"
    assert job.job_name == "Run Codex"
    assert job.job_input == {"prompt": "Review repository"}
    assert job.job_status == JobStatus.QUEUED
    assert job.updated_at == now
    assert job.root_initiator == initiator


def test_job_artifact_and_event_capture_execution_output() -> None:
    # Arrange
    now = datetime(2026, 6, 23, tzinfo=UTC)
    job_id = uuid4()

    # Act
    artifact = JobArtifact(
        artifact_id=uuid4(),
        job_id=job_id,
        name="changed.py",
        description=None,
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
        event_id=uuid4(),
        type="JobArtifactCreatedV1",
        source="job",
        version="v1",
        created_at=now,
        payload=JobArtifactCreatedPayload(
            job_id_issuer=job_id,
            artifact_id=str(artifact.artifact_id),
        ),
    )

    # Assert
    assert artifact.job_id == job_id
    assert artifact.role == ArtifactRole.OUTPUT
    assert event.type == "JobArtifactCreatedV1"
    assert event.payload.job_event_type == JobEventType.ARTIFACT_CREATED
    assert event.payload.artifact_id == str(artifact.artifact_id)
