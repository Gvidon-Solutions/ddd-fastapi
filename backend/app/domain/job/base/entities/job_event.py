"""Define job event entity."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.event import Event
from app.domain.job.base.value_objects.job_event_payload import JobEventPayload


@dataclass(kw_only=True)
class JobEvent(Event):
    """Represent a historical event emitted by a job."""

    payload: JobEventPayload | dict
