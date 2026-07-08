"""EventId value object tests."""

from uuid import UUID

from app.domain.event import new_event_id


def test_event_id_generates_uuid() -> None:
    # Act
    event_id = new_event_id()

    # Assert
    assert isinstance(event_id, UUID)
    assert str(event_id) == str(event_id)
