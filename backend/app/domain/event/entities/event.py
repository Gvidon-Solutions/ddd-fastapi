"""Define the Event entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(kw_only=True)
class Event:
    """Represent an immutable historical event envelope."""

    event_id: UUID
    type: str
    source: str
    version: str
    created_at: datetime
    payload: Any
