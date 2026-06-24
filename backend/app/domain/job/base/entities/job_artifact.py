"""Define the JobArtifact entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.job.base.value_objects import (
    ArtifactKind,
    ArtifactLocation,
    ArtifactRole,
)


@dataclass
class JobArtifact:
    """Represent a payload produced by a job."""

    artifact_id: UUID
    job_id: UUID
    name: str
    description: str | None
    role: ArtifactRole
    kind: ArtifactKind
    location: ArtifactLocation
    metadata: dict
    created_at: datetime
