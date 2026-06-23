"""Shared SQLModel datetime helpers."""

from datetime import UTC, datetime


def get_datetime_utc() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def ensure_datetime_utc(value: datetime) -> datetime:
    """Return a timezone-aware UTC timestamp from a persisted datetime."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
