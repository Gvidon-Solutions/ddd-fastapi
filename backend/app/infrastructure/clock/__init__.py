"""Expose clock adapters."""

from __future__ import annotations

from .system_clock import SystemClock, new_system_clock

__all__ = ("SystemClock", "new_system_clock")
