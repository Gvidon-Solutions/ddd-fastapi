"""Initiator SQLModel DTO."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from app.domain.job import ActorType, Initiator
from app.infrastructure.sqlmodel.datetime import get_datetime_utc


class InitiatorDTO(SQLModel, table=True):
    """Persisted initiator record."""

    __tablename__ = "initiator"

    initiator_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type: str = Field(max_length=32, index=True)
    external_id: str | None = Field(default=None, max_length=255, index=True)
    display_name: str | None = Field(default=None, max_length=255)
    initiator_metadata: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    def to_value_object(self) -> Initiator:
        """Convert this DTO to a domain initiator."""
        return Initiator(
            type=ActorType(self.type),
            external_id=self.external_id,
            display_name=self.display_name,
            metadata=self.initiator_metadata or None,
        )
