"""Job domain tests."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.job import (
    ActorType,
    File,
    FileKind,
    FileLocation,
    FileLocationType,
    FileStatus,
    Initiator,
    Job,
    JobEvent,
    JobEventPayload,
    JobFile,
    JobFileRole,
    JobStatus,
)


@dataclass(kw_only=True)
class JobFileCreatedPayload(JobEventPayload):
    """Represent a job file created payload."""

    file_id: str


def test_job_represents_a_queued_execution() -> None:
    now = datetime(2026, 6, 23, tzinfo=UTC)
    initiator = Initiator(
        type=ActorType.USER,
        external_id="anton",
        display_name="Anton",
    )

    job = Job(
        id=uuid4(),
        type="codex.run",
        version="v1",
        name="Run Codex",
        description="Run Codex against repository",
        input={"prompt": "Review repository"},
        result=None,
        status=JobStatus.QUEUED,
        initiator=initiator,
        parent_job_id=None,
        requested_at=now,
        updated_at=now,
        started_at=None,
        finished_at=None,
        error=None,
    )

    assert job.type == "codex.run"
    assert job.name == "Run Codex"
    assert job.input == {"prompt": "Review repository"}
    assert job.status == JobStatus.QUEUED
    assert job.updated_at == now
    assert job.initiator == initiator


def test_job_file_and_event_capture_execution_output() -> None:
    now = datetime(2026, 6, 23, tzinfo=UTC)
    job_id = uuid4()
    file = File(
        file_id=uuid4(),
        name="changed.py",
        kind=FileKind.FILE,
        location=FileLocation(
            type=FileLocationType.FILESYSTEM,
            uri="/tmp/jobs/changed.py",
        ),
        metadata={"filename": "changed.py", "source": "codex"},
        status=FileStatus.ACTIVE,
        delete_requested_at=None,
        delete_attempts=0,
        last_delete_error=None,
        created_at=now,
    )

    job_file = JobFile(
        job_id=job_id,
        file=file,
        role=JobFileRole.OUTPUT,
        description=None,
        created_at=now,
    )
    event = JobEvent(
        event_id=uuid4(),
        type="JobFileCreatedV1",
        source="job",
        version="v1",
        created_at=now,
        payload=JobFileCreatedPayload(file_id=str(file.file_id)),
    )

    assert job_file.job_id == job_id
    assert job_file.role == JobFileRole.OUTPUT
    assert event.type == "JobFileCreatedV1"
    assert event.payload.file_id == str(file.file_id)
