"""Define event entities."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.event import Event


@dataclass(kw_only=True)
class JobEventPayload:
    """Represent the job-specific payload for an emitted event."""

    job_id: UUID


@dataclass(kw_only=True)
class JobEvent(Event):
    """Represent a historical event emitted by a job."""

    payload: JobEventPayload | dict
