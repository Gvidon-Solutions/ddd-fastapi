"""Expose event value objects."""

from __future__ import annotations

from .event_id import EventId, new_event_id

__all__ = ("EventId", "new_event_id")
