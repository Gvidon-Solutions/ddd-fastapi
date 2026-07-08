"""Job summary response schema."""

from datetime import datetime
from uuid import UUID

from sqlmodel import SQLModel

from app.domain.job import JobSummary
from app.presentation.api.job.schemas.job_initiator_public import JobInitiatorPublic


class JobSummaryPublic(SQLModel):
    """Job summary response schema."""

    id: UUID
    type: str
    version: str
    name: str | None
    status: str
    initiator: JobInitiatorPublic
    parent_job_id: UUID | None
    requested_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def from_value_object(cls, summary: JobSummary) -> "JobSummaryPublic":
        """Build an API response from a domain value object."""
        return cls(
            id=summary.id,
            type=summary.type,
            version=summary.version,
            name=summary.name,
            status=summary.status.value,
            initiator=JobInitiatorPublic.from_value_object(summary.initiator),
            parent_job_id=summary.parent_job_id
            if summary.parent_job_id is not None
            else None,
            requested_at=summary.requested_at,
            updated_at=summary.updated_at,
            started_at=summary.started_at,
            finished_at=summary.finished_at,
        )
