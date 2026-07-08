"""Infrastructure event codec tests."""

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from app.domain.job import JobId
from app.domain.job.codex_run_job_use_case import (
    Event1CodexRunStarted,
    Event1CodexRunStartedPayload,
)
from app.infrastructure.event import dump_event, load_event_payload


def test_dump_event_serializes_identifier_values() -> None:
    # Arrange
    job_id = JobId(UUID("11111111-1111-1111-1111-111111111111"))
    event = Event1CodexRunStarted(
        created_at=datetime(2026, 7, 8, 12, 30, tzinfo=UTC),
        payload=Event1CodexRunStartedPayload(
            job_id=job_id,
            stage="codex_run",
            workdir="/tmp/work",
        ),
    )

    # Act
    record = dump_event(event)

    # Assert
    payload = cast(dict[str, object], record["payload"])
    assert isinstance(record["event_id"], str)
    assert record["type"] == "CodexRunStartedV1"
    assert record["source"] == "codex_run"
    assert record["version"] == "v1"
    assert record["created_at"] == "2026-07-08T12:30:00Z"
    assert payload["job_id"] == "11111111-1111-1111-1111-111111111111"
    assert payload["stage"] == "codex_run"
    assert payload["workdir"] == "/tmp/work"


def test_load_event_payload_restores_identifier_values() -> None:
    # Arrange
    record = {
        "job_id": "11111111-1111-1111-1111-111111111111",
        "stage": "codex_run",
        "workdir": "/tmp/work",
    }

    # Act
    payload = load_event_payload(record, Event1CodexRunStartedPayload)

    # Assert
    assert payload == Event1CodexRunStartedPayload(
        job_id=JobId(UUID("11111111-1111-1111-1111-111111111111")),
        stage="codex_run",
        workdir="/tmp/work",
    )
