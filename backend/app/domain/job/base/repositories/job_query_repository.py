"""Define read-side job query projections."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.job.base.entities import JobEvent, JobFile
from app.domain.job.base.value_objects import Initiator, JobError, JobStatus


@dataclass(frozen=True)
class JobSummary:
    """Small projection for job lists."""

    id: UUID
    type: str
    version: str
    name: str | None
    status: JobStatus
    initiator: Initiator
    parent_job_id: UUID | None
    requested_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(frozen=True)
class JobDetailProjection:
    """Detailed projection for job detail screens."""

    summary: JobSummary
    input: dict
    result: dict | None
    error: JobError | None
    files: tuple[JobFile, ...]
    events: tuple[JobEvent, ...]


class JobQueryRepository(ABC):
    """Read job projections without requiring executable contracts."""

    @abstractmethod
    async def get_detail(self, job_id: UUID) -> JobDetailProjection:
        """Return a job detail projection."""

    @abstractmethod
    async def list_by_initiator(self, initiator_external_id: str) -> list[JobSummary]:
        """Return jobs launched by an initiator external id."""
