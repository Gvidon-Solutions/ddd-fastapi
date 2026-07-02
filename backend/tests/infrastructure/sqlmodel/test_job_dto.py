"""Job SQLModel DTO tests."""

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
    JobError,
    JobEvent,
    JobEventPayload,
    JobFile,
    JobFileRole,
    JobStatus,
)
from app.domain.job.codex_auth_job_use_case import (
    CodexAuthInputV1,
    CodexAuthJobResult,
    Event3CodexAuthSucceeded,
    Event3CodexAuthSucceededPayload,
)
from app.infrastructure.sqlmodel.event import EventDTO
from app.infrastructure.sqlmodel.job import FileDTO, JobDTO, JobFileDTO


def test_job_dto_round_trips_entity_fields() -> None:
    initiator = Initiator(
        type=ActorType.USER,
        external_id="anton",
        display_name="Anton",
    )
    job = Job(
        id=uuid4(),
        type="codex.auth",
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


def test_file_and_job_file_dtos_round_trip_entity_fields() -> None:
    file = File(
        file_id=uuid4(),
        name="report.txt",
        kind=FileKind.FILE,
        location=FileLocation(
            type=FileLocationType.FILESYSTEM,
            uri="/tmp/report.txt",
        ),
        metadata={"filename": "report.txt"},
        status=FileStatus.ACTIVE,
        delete_requested_at=None,
        delete_attempts=0,
        last_delete_error=None,
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
    )
    job_file = JobFile(
        job_id=uuid4(),
        file=file,
        role=JobFileRole.OUTPUT,
        description=None,
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
    )

    file_entity = FileDTO.from_entity(file).to_entity()
    job_file_entity = JobFileDTO.from_entity(job_file).to_entity(FileDTO.from_entity(file))

    assert file_entity == file
    assert job_file_entity == job_file


def test_event_dto_round_trips_job_event_fields() -> None:
    event = JobEvent(
        event_id=uuid4(),
        type="JobFileCreatedV1",
        source="job",
        version="v1",
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        payload=JobEventPayload(),
    )

    entity = EventDTO.from_job_event(event).to_job_event()

    assert entity == event


def test_event_dto_casts_to_typed_event_dataclass() -> None:
    result = CodexAuthJobResult(authenticated=True)
    event = Event3CodexAuthSucceeded(
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        payload=Event3CodexAuthSucceededPayload(summary=result),
    )

    entity = EventDTO.from_job_event(event).to_entity()

    assert isinstance(entity, Event3CodexAuthSucceeded)
    assert isinstance(entity.payload, Event3CodexAuthSucceededPayload)
    assert entity.payload.summary == result
    assert entity == event
