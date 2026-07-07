"""Codex run job event 3."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from app.domain.event import EventId
from app.domain.file import FileId
from app.domain.job.base.entities import JobEvent
from app.domain.job.base.value_objects import JobEventPayload


@dataclass(kw_only=True)
class Event3CodexRunSucceededPayload(JobEventPayload):
    """Represent Codex run succeeded payload."""

    output_file_id: FileId | None
    log_files: int
    generated_files: int

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(kw_only=True)
class Event3CodexRunSucceeded(JobEvent):
    """Represent the Codex run succeeded event."""

    event_id: EventId = field(default_factory=EventId.generate, init=False)
    type: Literal["CodexRunSucceededV1"] = field(
        default="CodexRunSucceededV1",
        init=False,
    )
    source: str = field(default="", init=False)
    version: Literal["v1"] = field(default="v1", init=False)
    payload: Event3CodexRunSucceededPayload

    @staticmethod
    def source_prefix() -> str:
        """Return the source prefix for Codex run job events."""
        return "codex_run"

    def __post_init__(self) -> None:
        """Set the event source."""
        self.source = self.source_prefix()
