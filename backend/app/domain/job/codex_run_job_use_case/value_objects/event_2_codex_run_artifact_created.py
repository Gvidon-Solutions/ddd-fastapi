"""Codex run job event 2."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal
from uuid import UUID, uuid4

from app.domain.job.base.entities import JobEvent, JobEventPayload
from app.domain.job.base.value_objects import JobEventType


@dataclass(kw_only=True)
class Event2CodexRunArtifactCreatedPayload(JobEventPayload):
    """Represent Codex run artifact created payload."""

    job_event_type: JobEventType = field(
        default=JobEventType.ARTIFACT_CREATED,
        init=False,
    )
    message: str | None = field(init=False)
    artifact_id: str
    filename: str

    def __post_init__(self) -> None:
        """Set the artifact creation message."""
        self.message = f"Created artifact {self.filename}"

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(kw_only=True)
class Event2CodexRunArtifactCreated(JobEvent):
    """Represent the Codex run artifact created event."""

    event_id: UUID = field(default_factory=uuid4, init=False)
    type: Literal["CodexRunArtifactCreatedV1"] = field(
        default="CodexRunArtifactCreatedV1",
        init=False,
    )
    source: str = field(default="", init=False)
    version: Literal["v1"] = field(default="v1", init=False)
    payload: Event2CodexRunArtifactCreatedPayload

    @staticmethod
    def source_prefix() -> str:
        """Return the source prefix for Codex run job events."""
        return "codex_run"

    def __post_init__(self) -> None:
        """Set the event source to the issuing Codex run job."""
        self.source = f"{self.source_prefix()}/{self.payload.job_id_issuer}"
