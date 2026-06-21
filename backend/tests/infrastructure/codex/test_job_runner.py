"""Codex job runner tests."""

from pydantic import BaseModel

from app.domain.codex_job.value_objects import CodexJobPrompt
from app.infrastructure.codex.job_runner import _event_payload, _event_type


class FakePydanticEvent(BaseModel):
    """Fake OpenAI Agents stream event."""

    type: str
    text: str


def test_event_type_uses_event_type_field() -> None:
    # Arrange
    event = FakePydanticEvent(type="run_item_stream_event", text="hello")

    # Act
    event_type = _event_type(event)

    # Assert
    assert event_type == "run_item_stream_event"


def test_event_payload_serializes_pydantic_event() -> None:
    # Arrange
    event = FakePydanticEvent(type="raw_response_event", text="hello")

    # Act
    payload = _event_payload(event)

    # Assert
    assert payload == '{"type":"raw_response_event","text":"hello"}'


def test_event_payload_serializes_value_objects() -> None:
    # Arrange
    event = {"prompt": CodexJobPrompt("Review repository")}

    # Act
    payload = _event_payload(event)

    # Assert
    assert payload == '{"prompt": "Review repository"}'
