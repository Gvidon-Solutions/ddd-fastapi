"""EventId value object tests."""

from uuid import UUID

from app.domain.event import EventId


def test_event_id_generates_uuid() -> None:
    # Act
    event_id = EventId.generate()

    # Assert
    assert isinstance(event_id.value, UUID)
    assert str(event_id) == str(event_id.value)
