"""JobFile SQLModel DTO."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from app.domain.job import JobFile, JobFileRole
from app.infrastructure.sqlmodel.datetime import ensure_datetime_utc, get_datetime_utc
from app.infrastructure.sqlmodel.job.file_dto import FileDTO


class JobFileDTO(SQLModel, table=True):
    """Persisted job-file association."""

    __tablename__ = "job_file"

    job_id: uuid.UUID = Field(foreign_key="job.job_id", primary_key=True)
    file_id: uuid.UUID = Field(foreign_key="file.file_id", primary_key=True)
    role: str = Field(max_length=32, primary_key=True)
    description: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    def to_entity(self, file: FileDTO) -> JobFile:
        """Convert this DTO to a domain association."""
        return JobFile(
            job_id=self.job_id,
            file=file.to_entity(),
            role=JobFileRole(self.role),
            description=self.description,
            created_at=ensure_datetime_utc(self.created_at),
        )

    @staticmethod
    def from_entity(job_file: JobFile) -> JobFileDTO:
        """Build a DTO from a domain association."""
        return JobFileDTO(
            job_id=job_file.job_id,
            file_id=job_file.file.file_id,
            role=job_file.role.value,
            description=job_file.description,
            created_at=job_file.created_at,
        )
