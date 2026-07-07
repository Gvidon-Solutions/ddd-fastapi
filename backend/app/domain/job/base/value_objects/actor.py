"""Define the job initiator value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.domain.job.base.value_objects.actor_type import ActorType

if TYPE_CHECKING:
    from app.domain.user.entities import User


@dataclass(frozen=True)
class Initiator:
    """Represent the source that initiated a job chain."""

    type: ActorType
    external_id: str | None = None
    display_name: str | None = None
    metadata: dict | None = None

    @classmethod
    def from_user(cls, user: User) -> Initiator:
        """Build an initiator for a user-owned job."""
        return cls(
            type=ActorType.USER,
            external_id=str(user.id),
            display_name=user.email.value,
        )
