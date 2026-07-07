"""Job file response schema."""

from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.domain.job import JobFile


class JobFilePublic(SQLModel):
    """Job file response schema."""

    file_id: UUID
    job_id: UUID
    role: str
    name: str
    kind: str
    location_uri: str
    metadata_: dict = Field(alias="metadata")
    status: str
    description: str | None
    attached_at: datetime
    created_at: datetime

    @classmethod
    def from_entity(cls, job_file: JobFile) -> "JobFilePublic":
        """Build an API response from a domain entity."""
        return cls(
            file_id=job_file.file_id.value,
            job_id=job_file.job_id.value,
            role=job_file.role.value,
            name=job_file.name,
            kind=job_file.kind.value,
            location_uri=job_file.location.uri,
            metadata=job_file.metadata,
            status=job_file.status.value,
            description=job_file.description,
            attached_at=job_file.attached_at,
            created_at=job_file.created_at,
        )
