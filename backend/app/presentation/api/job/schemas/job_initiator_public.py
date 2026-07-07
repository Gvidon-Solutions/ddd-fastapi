"""Job initiator response schema."""

from sqlmodel import Field, SQLModel

from app.domain.job import Initiator


class JobInitiatorPublic(SQLModel):
    """Job initiator response schema."""

    type: str
    external_id: str | None
    display_name: str | None
    metadata_: dict = Field(alias="metadata")

    @staticmethod
    def from_value_object(initiator: Initiator) -> "JobInitiatorPublic":
        """Build an API response from a domain value object."""
        return JobInitiatorPublic(
            type=initiator.type.value,
            external_id=initiator.external_id,
            display_name=initiator.display_name,
            metadata=initiator.metadata or {},
        )
