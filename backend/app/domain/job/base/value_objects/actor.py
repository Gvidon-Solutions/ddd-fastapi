"""Define the job initiator value object."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.job.base.value_objects.actor_type import ActorType


@dataclass(frozen=True, eq=False)
class Initiator:
    """Represent the source that initiated a job chain."""

    type: ActorType
    external_id: str | None = None
    display_name: str | None = None
    metadata: dict | None = None

    @property
    def id(self) -> str | None:
        """Return the legacy external identifier name."""
        return self.external_id

    def __eq__(self, other: object) -> bool:
        """Compare initiator values across Initiator/Actor aliases."""
        if not isinstance(other, Initiator):
            return NotImplemented
        return (
            self.type == other.type
            and self.external_id == other.external_id
            and self.display_name == other.display_name
            and self.metadata == other.metadata
        )


class Actor(Initiator):
    """Backward-compatible name for Initiator."""

    def __init__(
        self,
        type: ActorType,
        id: str | None = None,
        display_name: str | None = None,
        metadata: dict | None = None,
        external_id: str | None = None,
    ) -> None:
        """Create an initiator using either external_id or the old id name."""
        super().__init__(
            type=type,
            external_id=external_id if external_id is not None else id,
            display_name=display_name,
            metadata=metadata,
        )
