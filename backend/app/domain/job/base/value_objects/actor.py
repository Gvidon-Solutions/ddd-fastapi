"""Define the job initiator value object."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.job.base.value_objects.actor_type import ActorType


@dataclass(frozen=True)
class Initiator:
    """Represent the source that initiated a job chain."""

    type: ActorType
    external_id: str | None = None
    display_name: str | None = None
    metadata: dict | None = None
