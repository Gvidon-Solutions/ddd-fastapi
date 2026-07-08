"""Codex run job event 6."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from app.domain.event import EventId, new_event_id
from app.domain.job.base.entities import JobEvent
from app.domain.job.base.value_objects import JobEventPayload


@dataclass(kw_only=True)
class Event6CodexExecOutputPayload(JobEventPayload):
    """Represent one Codex exec output line."""

    channel: Literal["stdout", "stderr"]
    line_number: int
    line: str

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(kw_only=True)
class Event6CodexExecOutput(JobEvent):
    """Represent a streamed Codex exec output event."""

    event_id: EventId = field(default_factory=new_event_id, init=False)
    type: Literal["CodexExecOutputV1"] = field(
        default="CodexExecOutputV1",
        init=False,
    )
    source: str = field(default="", init=False)
    version: Literal["v1"] = field(default="v1", init=False)
    payload: Event6CodexExecOutputPayload

    @staticmethod
    def source_prefix() -> str:
        """Return the source prefix for Codex exec output events."""
        return "codex_exec"

    def __post_init__(self) -> None:
        """Set the event source."""
        self.source = self.source_prefix()
