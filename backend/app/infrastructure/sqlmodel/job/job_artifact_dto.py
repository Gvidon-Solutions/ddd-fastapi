"""JobArtifact SQLModel DTO."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from app.domain.job import (
    ArtifactKind,
    ArtifactLocation,
    ArtifactLocationType,
    ArtifactRole,
    JobArtifact,
)
from app.infrastructure.sqlmodel.datetime import ensure_datetime_utc, get_datetime_utc


class JobArtifactDTO(SQLModel, table=True):
    """Persisted job artifact record."""

    __tablename__ = "job_artifact"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="job.id", nullable=False, index=True)
    role: str = Field(max_length=32, index=True)
    kind: str = Field(max_length=32)
    location: dict = Field(sa_column=Column(JSON, nullable=False))
    artifact_metadata: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    def to_entity(self) -> JobArtifact:
        """Convert this persistence DTO to a domain entity."""
        return JobArtifact(
            id=self.id,
            job_id=self.job_id,
            role=ArtifactRole(self.role),
            kind=ArtifactKind(self.kind),
            location=ArtifactLocation(
                type=ArtifactLocationType(self.location["type"]),
                uri=self.location.get("uri"),
            ),
            metadata=self.artifact_metadata,
            created_at=ensure_datetime_utc(self.created_at or get_datetime_utc()),
        )

    @staticmethod
    def from_entity(artifact: JobArtifact) -> JobArtifactDTO:
        """Build a persistence DTO from a domain entity."""
        return JobArtifactDTO(
            id=artifact.id,
            job_id=artifact.job_id,
            role=artifact.role.value,
            kind=artifact.kind.value,
            location={
                "type": artifact.location.type.value,
                "uri": artifact.location.uri,
            },
            artifact_metadata=artifact.metadata,
            created_at=artifact.created_at,
        )
