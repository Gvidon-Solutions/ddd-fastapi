"""Job domain tests."""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.event import EventId
from app.domain.file import File, FileId, FileKind, FileLocation, FileStatus
from app.domain.job import (
    ActorType,
    DuplicateJobContractError,
    Initiator,
    Job,
    JobDeleteNotAllowedError,
    JobEvent,
    JobEventPayload,
    JobFile,
    JobFileRole,
    JobId,
    JobStatus,
)


@dataclass(kw_only=True)
class JobFileCreatedPayload(JobEventPayload):
    """Represent a job file created payload."""

    file_id: str


def test_job_represents_a_pending_execution() -> None:
    now = datetime(2026, 6, 23, tzinfo=UTC)
    initiator = Initiator(
        type=ActorType.USER,
        external_id="anton",
        display_name="Anton",
    )

    job = Job(
        id=JobId.generate(),
        type="execute_codex_run_job_use_case",
        version="v1",
        name="Run Codex",
        description="Run Codex against repository",
        input={"prompt": "Review repository"},
        result=None,
        status=JobStatus.PENDING,
        initiator=initiator,
        parent_job_id=None,
        requested_at=now,
        updated_at=now,
        started_at=None,
        finished_at=None,
        error=None,
    )

    assert job.type == "execute_codex_run_job_use_case"
    assert job.name == "Run Codex"
    assert job.input == {"prompt": "Review repository"}
    assert job.status == JobStatus.PENDING
    assert job.updated_at == now
    assert job.initiator == initiator


def test_job_file_and_event_capture_execution_output() -> None:
    now = datetime(2026, 6, 23, tzinfo=UTC)
    job_id = JobId.generate()
    file = File(
        file_id=FileId.generate(),
        name="changed.py",
        kind=FileKind.FILE,
        location=FileLocation(
            uri="file:///tmp/jobs/changed.py",
        ),
        metadata={"filename": "changed.py", "source": "codex"},
        status=FileStatus.ACTIVE,
        delete_requested_at=None,
        delete_attempts=0,
        last_delete_error=None,
        created_at=now,
    )

    job_file = JobFile(
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
        role=JobFileRole.OUTPUT,
        description=None,
        attached_at=now,
    )
    event = JobEvent(
        event_id=EventId.generate(),
        type="JobFileCreatedV1",
        source="job",
        version="v1",
        created_at=now,
        payload=JobFileCreatedPayload(job_id=job_id, file_id=str(file.file_id)),
    )

    assert job_file.job_id == job_id
    assert job_file.role == JobFileRole.OUTPUT
    assert event.type == "JobFileCreatedV1"
    assert isinstance(event.payload, JobFileCreatedPayload)
    assert event.payload.job_id == job_id
    assert event.payload.file_id == str(file.file_id)


def test_job_exceptions_expose_default_and_custom_detail() -> None:
    duplicate = DuplicateJobContractError()
    delete_not_allowed = JobDeleteNotAllowedError("job is still running")

    assert duplicate.detail == "Job contract already exists."
    assert str(duplicate) == duplicate.detail
    assert delete_not_allowed.detail == "job is still running"
    assert str(delete_not_allowed) == "job is still running"
