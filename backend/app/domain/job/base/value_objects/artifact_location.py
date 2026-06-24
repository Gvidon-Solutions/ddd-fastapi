"""Define the ArtifactLocation value object."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.job.base.value_objects.artifact_location_type import ArtifactLocationType


@dataclass(frozen=True)
class ArtifactLocation:
    """Represent the storage location of an artifact payload."""

    type: ArtifactLocationType
    uri: str | None = None
