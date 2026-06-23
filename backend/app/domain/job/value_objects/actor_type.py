"""Define actor types."""

from __future__ import annotations

from enum import StrEnum


class ActorType(StrEnum):
    """Represent the source that initiated a job chain."""

    USER = "user"
    SYSTEM = "system"
    SCHEDULE = "schedule"
    API = "api"
