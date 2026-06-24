"""Expose the event domain."""

from __future__ import annotations

from .entities import Event
from .registry import get_event_class, get_event_type_registry

__all__ = ("Event", "get_event_class", "get_event_type_registry")
