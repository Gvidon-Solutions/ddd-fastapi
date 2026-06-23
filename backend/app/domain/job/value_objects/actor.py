"""Define the Actor value object."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.job.value_objects.actor_type import ActorType


@dataclass(frozen=True)
class Actor:
    """Represent the actor that initiated a job chain."""

    type: ActorType
    id: str | None = None
    display_name: str | None = None
