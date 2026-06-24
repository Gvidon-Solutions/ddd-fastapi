"""Codex run job event 4."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal
from uuid import UUID, uuid4

from app.domain.job.base.entities import JobEvent, JobEventPayload
from app.domain.job.base.value_objects import JobEventType


@dataclass(kw_only=True)
class Event4CodexRunFailedPayload(JobEventPayload):
    """Represent Codex run failed payload."""

    job_event_type: JobEventType = field(default=JobEventType.FAILED, init=False)
    message: str | None = field(init=False)
    error: str

    def __post_init__(self) -> None:
        """Set the failure message."""
        self.message = self.error

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(kw_only=True)
class Event4CodexRunFailed(JobEvent):
    """Represent the Codex run failed event."""

    event_id: UUID = field(default_factory=uuid4, init=False)
    type: Literal["CodexRunFailedV1"] = field(
        default="CodexRunFailedV1",
        init=False,
    )
    source: str = field(default="", init=False)
    version: Literal["v1"] = field(default="v1", init=False)
    payload: Event4CodexRunFailedPayload

    @staticmethod
    def source_prefix() -> str:
        """Return the source prefix for Codex run job events."""
        return "codex_run"

    def __post_init__(self) -> None:
        """Set the event source to the issuing Codex run job."""
        self.source = f"{self.source_prefix()}/{self.payload.job_id_issuer}"
