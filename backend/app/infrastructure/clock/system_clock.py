"""System clock adapter."""

from __future__ import annotations

from datetime import datetime

from app.infrastructure.sqlmodel.datetime import get_datetime_utc
from app.usecase.job import Clock


class SystemClock(Clock):
    """Provide current UTC time from the system clock."""

    def now(self) -> datetime:
        """Return the current UTC time."""
        return get_datetime_utc()


def new_system_clock() -> Clock:
    """Create a system clock."""
    return SystemClock()
