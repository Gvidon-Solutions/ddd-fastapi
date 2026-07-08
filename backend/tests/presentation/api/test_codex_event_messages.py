"""Codex realtime event message tests."""

from app.presentation.api.codex import to_codex_job_event_message


def test_codex_event_message_converts_exec_output_event() -> None:
    # Arrange
    event = {
        "event_id": "22222222-2222-2222-2222-222222222222",
        "type": "CodexExecOutputV1",
        "source": "codex_exec",
        "version": "v1",
        "created_at": "2026-07-08T12:30:00Z",
        "payload": {
            "job_id": "11111111-1111-1111-1111-111111111111",
            "channel": "stdout",
            "line_number": 1,
            "line": "running",
        },
    }

    # Act
    message = to_codex_job_event_message(stream_id="1-0", event=event)

    # Assert
    assert message is not None
    assert message.stream_id == "1-0"
    assert message.event.type == "CodexExecOutputV1"
    assert message.event.payload.channel == "stdout"
    assert message.event.payload.line == "running"


def test_codex_event_message_ignores_non_codex_event() -> None:
    # Arrange
    event = {
        "event_id": "22222222-2222-2222-2222-222222222222",
        "type": "OtherEventV1",
        "source": "other",
        "version": "v1",
        "created_at": "2026-07-08T12:30:00Z",
        "payload": {},
    }

    # Act
    message = to_codex_job_event_message(stream_id="1-0", event=event)

    # Assert
    assert message is None
