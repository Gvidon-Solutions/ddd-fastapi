"""Define the Event entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.domain.event.value_objects import EventId


@dataclass(kw_only=True)
class Event:
    """Represent an immutable historical event envelope."""

    event_id: EventId
    type: str
    source: str
    version: str
    created_at: datetime
    payload: Any
