"""Codex run job event 5."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal
from uuid import UUID, uuid4

from app.domain.job.base.entities import JobEvent
from app.domain.job.base.value_objects import JobEventPayload


@dataclass(kw_only=True)
class Event5CodexRunCancelledPayload(JobEventPayload):
    """Represent Codex run cancelled payload."""

    reason: str = "Job cancelled"

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(kw_only=True)
class Event5CodexRunCancelled(JobEvent):
    """Represent the Codex run cancelled event."""

    event_id: UUID = field(default_factory=uuid4, init=False)
    type: Literal["CodexRunCancelledV1"] = field(
        default="CodexRunCancelledV1",
        init=False,
    )
    source: str = field(default="", init=False)
    version: Literal["v1"] = field(default="v1", init=False)
    payload: Event5CodexRunCancelledPayload

    @staticmethod
    def source_prefix() -> str:
        """Return the source prefix for Codex run job events."""
        return "codex_run"

    def __post_init__(self) -> None:
        """Set the event source."""
        self.source = self.source_prefix()
