"""Define the Event identifier type."""

from typing import NewType
from uuid import UUID, uuid4

EventId = NewType("EventId", UUID)


def new_event_id() -> EventId:
    """Generate a new identifier for an event."""
    return EventId(uuid4())
