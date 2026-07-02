"""Codex auth job event 3."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal
from uuid import UUID, uuid4

from app.domain.job.base.entities import JobEvent, JobEventPayload
from app.domain.job.base.value_objects import JobEventType
from app.domain.job.codex_auth_job_use_case.value_objects.contracts import (
    CodexAuthJobResult,
)


@dataclass(kw_only=True)
class Event3CodexAuthSucceededPayload(JobEventPayload):
    """Represent event 3 payload."""

    job_event_type: JobEventType = field(default=JobEventType.SUCCEEDED, init=False)
    message: str | None = field(default="Codex auth completed", init=False)
    summary: CodexAuthJobResult

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(kw_only=True)
class Event3CodexAuthSucceeded(JobEvent):
    """Represent the Codex auth succeeded event."""

    event_id: UUID = field(default_factory=uuid4, init=False)
    type: Literal["CodexAuthSucceededV1"] = field(
        default="CodexAuthSucceededV1",
        init=False,
    )
    source: str = field(default="", init=False)
    version: Literal["v1"] = field(default="v1", init=False)
    payload: Event3CodexAuthSucceededPayload

    @staticmethod
    def source_prefix() -> str:
        """Return the source prefix for Codex auth job events."""
        return "codex_auth_job_use_case"

    def __post_init__(self) -> None:
        """Set the event source to the issuing Codex auth job."""
        self.source = f"{self.source_prefix()}/{self.payload.job_id_issuer}"
