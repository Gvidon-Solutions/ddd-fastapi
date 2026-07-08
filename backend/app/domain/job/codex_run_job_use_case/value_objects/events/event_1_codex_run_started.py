"""Codex run job event 1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from app.domain.event import EventId, new_event_id
from app.domain.job.base.entities import JobEvent
from app.domain.job.base.value_objects import JobEventPayload


@dataclass(kw_only=True)
class Event1CodexRunStartedPayload(JobEventPayload):
    """Represent Codex run started payload."""

    stage: str
    workdir: str

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(kw_only=True)
class Event1CodexRunStarted(JobEvent):
    """Represent the Codex run started event."""

    event_id: EventId = field(default_factory=new_event_id, init=False)
    type: Literal["CodexRunStartedV1"] = field(
        default="CodexRunStartedV1",
        init=False,
    )
    source: str = field(default="", init=False)
    version: Literal["v1"] = field(default="v1", init=False)
    payload: Event1CodexRunStartedPayload

    @staticmethod
    def source_prefix() -> str:
        """Return the source prefix for Codex run job events."""
        return "codex_run"

    def __post_init__(self) -> None:
        """Set the event source."""
        self.source = self.source_prefix()
