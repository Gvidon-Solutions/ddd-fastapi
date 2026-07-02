"""Codex auth job event 4."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal
from uuid import UUID, uuid4

from app.domain.job.base.entities import JobEvent, JobEventPayload


@dataclass(kw_only=True)
class Event4CodexAuthFailedPayload(JobEventPayload):
    """Represent event 4 payload."""

    error: str

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(kw_only=True)
class Event4CodexAuthFailed(JobEvent):
    """Represent the Codex auth failed event."""

    event_id: UUID = field(default_factory=uuid4, init=False)
    type: Literal["CodexAuthFailedV1"] = field(
        default="CodexAuthFailedV1",
        init=False,
    )
    source: str = field(default="", init=False)
    version: Literal["v1"] = field(default="v1", init=False)
    payload: Event4CodexAuthFailedPayload

    @staticmethod
    def source_prefix() -> str:
        """Return the source prefix for Codex auth job events."""
        return "codex_auth_job_use_case"

    def __post_init__(self) -> None:
        """Set the event source."""
        self.source = self.source_prefix()
