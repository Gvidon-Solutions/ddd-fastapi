"""Codex auth job event 3."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.job.base.entities import JobEvent
from app.domain.job.base.value_objects import JobEventType
from app.domain.job.codex_auth_job_use_case.value_objects.codex_auth_job_result import (
    CodexAuthJobResult,
)


@dataclass(frozen=True)
class Event3CodexAuthSucceededData:
    """Represent event 3 data."""

    summary: CodexAuthJobResult

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(kw_only=True)
class Event3CodexAuthSucceeded(JobEvent):
    """Represent the Codex auth succeeded event."""

    id: UUID = field(default_factory=uuid4, init=False)
    type: JobEventType = field(default=JobEventType.SUCCEEDED, init=False)
    data: Event3CodexAuthSucceededData
    message: str | None = field(default="Codex auth completed", init=False)
