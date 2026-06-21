"""AgentEventPayload value object tests."""

import pytest

from app.domain.agent.value_objects import AgentEventPayload


def test_agent_event_payload_accepts_json_shape() -> None:
    # Arrange
    value = {"message": "started", "step": 1, "meta": {"ok": True}}

    # Act
    payload = AgentEventPayload(value)

    # Assert
    assert payload.value == value


def test_agent_event_payload_rejects_empty_payload() -> None:
    # Arrange
    value = {}

    # Act / Assert
    with pytest.raises(ValueError, match="required"):
        AgentEventPayload(value)


def test_agent_event_payload_rejects_non_string_keys() -> None:
    # Arrange
    value = {1: "invalid"}  # type: ignore[dict-item]

    # Act / Assert
    with pytest.raises(ValueError, match="keys"):
        AgentEventPayload(value)


def test_agent_event_payload_rejects_non_json_values() -> None:
    # Arrange
    value = {"invalid": object()}

    # Act / Assert
    with pytest.raises(ValueError, match="JSON"):
        AgentEventPayload(value)  # type: ignore[arg-type]
