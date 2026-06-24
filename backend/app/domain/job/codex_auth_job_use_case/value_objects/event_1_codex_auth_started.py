"""Codex auth job event 1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.job.base.entities import JobEvent
from app.domain.job.base.value_objects import JobEventType


@dataclass(frozen=True)
class Event1CodexAuthStartedData:
    """Represent event 1 data."""

    stage: str = "codex_auth"

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(kw_only=True)
class Event1CodexAuthStarted(JobEvent):
    """Represent the Codex auth started event."""

    id: UUID = field(default_factory=uuid4, init=False)
    type: JobEventType = field(default=JobEventType.STARTED, init=False)
    data: Event1CodexAuthStartedData = field(
        default_factory=Event1CodexAuthStartedData,
    )
    message: str | None = field(default="Started Codex device auth", init=False)
