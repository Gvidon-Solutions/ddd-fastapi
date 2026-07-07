"""Job SQLModel DTO tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.event import EventId
from app.domain.file import File, FileId, FileKind, FileLocation, FileStatus
from app.domain.job import (
    ActorType,
    Initiator,
    JobError,
    JobEvent,
    JobEventPayload,
    JobFile,
    JobFileRole,
    JobId,
    JobSerializationError,
    JobStatus,
)
from app.domain.job.codex_auth_job_use_case import (
    CodexAuthInputV1,
    CodexAuthJobV1,
    CodexAuthResult,
    Event3CodexAuthSucceeded,
    Event3CodexAuthSucceededPayload,
)
from app.domain.job.codex_run_job_use_case import CodexRunInputV1
from app.infrastructure.sqlmodel.event import EventDTO
from app.infrastructure.sqlmodel.file import FileDTO
from app.infrastructure.sqlmodel.job import JobDTO, JobFileDTO
from app.infrastructure.sqlmodel.job.payload_codec import dump_payload, load_payload


def test_job_dto_round_trips_entity_fields() -> None:
    initiator = Initiator(
        type=ActorType.USER,
        external_id="anton",
        display_name="Anton",
    )
    job = CodexAuthJobV1(
        id=JobId.generate(),
        type="execute_codex_auth_job_use_case",
        version="v1",
        name="Codex auth",
        description="Authenticate Codex",
        input=CodexAuthInputV1(),
        result=None,
        status=JobStatus.RUNNING,
        initiator=initiator,
        parent_job_id=None,
        requested_at=datetime(2026, 6, 23, tzinfo=UTC),
        updated_at=datetime(2026, 6, 23, 0, 30, tzinfo=UTC),
        started_at=datetime(2026, 6, 23, 1, tzinfo=UTC),
        finished_at=None,
        error=JobError(
            code="RuntimeError",
            message="failed",
            details={"step": "codex"},
        ),
    )

    dto = JobDTO.from_entity(job, initiator_id=uuid4())
    entity = dto.to_entity(initiator)

    assert entity == job


def test_payload_codec_round_trips_stdlib_dataclass_type() -> None:
    payload = CodexRunInputV1(prompt="Review repository")

    record = dump_payload(payload)
    entity = load_payload(record, CodexRunInputV1)

    assert record == {"prompt": "Review repository", "workdir": None}
    assert type(entity) is CodexRunInputV1
    assert entity == payload


def test_payload_codec_rejects_unknown_fields() -> None:
    with pytest.raises(JobSerializationError) as exc:
        load_payload(
            {"prompt": "Review repository", "unexpected": True},
            CodexRunInputV1,
        )

    assert "Unexpected keyword argument" in str(exc.value)


def test_file_and_job_file_dtos_round_trip_entity_fields() -> None:
    file = File(
        file_id=FileId.generate(),
        name="report.txt",
        kind=FileKind.FILE,
        location=FileLocation(
            uri="file:///tmp/report.txt",
        ),
        metadata={"filename": "report.txt"},
        status=FileStatus.ACTIVE,
        delete_requested_at=None,
        delete_attempts=0,
        last_delete_error=None,
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
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
        job_id=JobId.generate(),
        role=JobFileRole.OUTPUT,
        description=None,
        attached_at=datetime(2026, 6, 23, tzinfo=UTC),
    )

    file_entity = FileDTO.from_entity(file).to_entity()
    job_file_entity = JobFileDTO.from_entity(job_file).to_entity(FileDTO.from_entity(file))

    assert file_entity == file
    assert job_file_entity == job_file


def test_event_dto_round_trips_job_event_fields() -> None:
    job_id = JobId.generate()
    event = JobEvent(
        event_id=EventId.generate(),
        type="JobFileCreatedV1",
        source="job",
        version="v1",
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        payload=JobEventPayload(job_id=job_id),
    )

    entity = EventDTO.from_job_event(event).to_job_event()

    assert entity == event


def test_event_dto_preserves_unknown_job_event_payload() -> None:
    job_id = JobId.generate()
    event = JobEvent(
        event_id=EventId.generate(),
        type="UnknownJobEventV1",
        source="job",
        version="v1",
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        payload={"job_id": job_id.value, "file_id": "file-1"},
    )

    entity = EventDTO.from_job_event(event).to_job_event()

    assert entity.event_id == event.event_id
    assert entity.payload == {"job_id": str(job_id.value), "file_id": "file-1"}


def test_event_dto_casts_to_typed_event_dataclass() -> None:
    job_id = JobId.generate()
    result = CodexAuthResult(authenticated=True)
    event = Event3CodexAuthSucceeded(
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        payload=Event3CodexAuthSucceededPayload(job_id=job_id, summary=result),
    )

    entity = EventDTO.from_job_event(event).to_entity()

    assert isinstance(entity, Event3CodexAuthSucceeded)
    assert isinstance(entity.payload, Event3CodexAuthSucceededPayload)
    assert entity.payload.summary == result
    assert entity == event
