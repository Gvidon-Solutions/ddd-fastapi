"""Define the JobArtifact repository contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.job.base.entities import JobArtifact
from app.domain.job.base.value_objects import ArtifactRole


class JobArtifactRepository(ABC):
    """Persist job artifacts."""

    @abstractmethod
    async def create(self, artifact: JobArtifact) -> None:
        """Create a new artifact."""

    @abstractmethod
    async def list_by_job(
        self,
        job_id: UUID,
        role: ArtifactRole | None = None,
    ) -> list[JobArtifact]:
        """Return artifacts for a job."""
