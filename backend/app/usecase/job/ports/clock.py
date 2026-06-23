"""Define the clock port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class Clock(ABC):
    """Provide application time without coupling use cases to the system clock."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current time."""
