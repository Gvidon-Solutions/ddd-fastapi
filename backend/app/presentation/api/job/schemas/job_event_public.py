"""Job event response schema."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlmodel import SQLModel

from app.domain.job import JobEvent


class JobEventPublic(SQLModel):
    """Job event response schema."""

    event_id: UUID
    type: str
    source: str
    version: str
    created_at: datetime
    payload: dict[str, Any]

    @staticmethod
    def from_entity(event: JobEvent) -> "JobEventPublic":
        """Build an API response from a domain entity."""
        return JobEventPublic(
            event_id=event.event_id,
            type=event.type,
            source=event.source,
            version=event.version,
            created_at=event.created_at,
            payload=jsonable_encoder(event.payload),
        )
