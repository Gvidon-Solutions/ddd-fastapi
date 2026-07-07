"""Codex auth job event 1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from app.domain.event import EventId
from app.domain.job.base.entities import JobEvent
from app.domain.job.base.value_objects import JobEventPayload


@dataclass(kw_only=True)
class Event1CodexAuthStartedPayload(JobEventPayload):
    """Represent event 1 payload."""

    stage: str = "codex_auth"

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(kw_only=True)
class Event1CodexAuthStarted(JobEvent):
    """Represent the Codex auth started event."""

    event_id: EventId = field(default_factory=EventId.generate, init=False)
    type: Literal["CodexAuthStartedV1"] = field(
        default="CodexAuthStartedV1",
        init=False,
    )
    source: str = field(default="", init=False)
    version: Literal["v1"] = field(default="v1", init=False)
    payload: Event1CodexAuthStartedPayload

    @staticmethod
    def source_prefix() -> str:
        """Return the source prefix for Codex auth job events."""
        return "codex_auth_job_use_case"

    def __post_init__(self) -> None:
        """Set the event source."""
        self.source = self.source_prefix()
