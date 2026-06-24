"""Codex auth job event 4."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.job.base.entities import JobEvent
from app.domain.job.base.value_objects import JobEventType


@dataclass(frozen=True)
class Event4CodexAuthFailedData:
    """Represent event 4 data."""

    error: str

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(kw_only=True)
class Event4CodexAuthFailed(JobEvent):
    """Represent the Codex auth failed event."""

    id: UUID = field(default_factory=uuid4, init=False)
    type: JobEventType = field(default=JobEventType.FAILED, init=False)
    data: Event4CodexAuthFailedData
    message: str | None = field(default="Codex auth failed", init=False)
