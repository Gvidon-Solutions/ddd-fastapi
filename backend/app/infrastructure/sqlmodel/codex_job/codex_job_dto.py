"""CodexJob SQLModel DTO."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from app.domain.codex_job.entities import CodexJob
from app.domain.codex_job.value_objects import (
    CodexJobId,
    CodexJobPrompt,
    CodexJobStatus,
)
from app.infrastructure.sqlmodel.datetime import get_datetime_utc


class CodexJobDTO(SQLModel, table=True):
    """Persisted Codex job record."""

    __tablename__ = "codex_job"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    prompt: str = Field(min_length=1)
    status: str = Field(max_length=32)
    backend_job_id: str | None = Field(default=None, max_length=255)
    result: str | None = Field(default=None)
    error_message: str | None = Field(default=None)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    started_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    def to_entity(self) -> CodexJob:
        """Convert this persistence DTO to a domain entity."""
        return CodexJob(
            id=CodexJobId(self.id),
            prompt=CodexJobPrompt(self.prompt),
            status=CodexJobStatus(self.status),
            backend_job_id=self.backend_job_id,
            result=self.result,
            error_message=self.error_message,
            created_at=self.created_at or get_datetime_utc(),
            started_at=self.started_at,
            finished_at=self.finished_at,
        )

    @staticmethod
    def from_entity(codex_job: CodexJob) -> "CodexJobDTO":
        """Build a persistence DTO from a domain entity."""
        return CodexJobDTO(
            id=codex_job.id.value,
            prompt=codex_job.prompt.value,
            status=codex_job.status.value,
            backend_job_id=codex_job.backend_job_id,
            result=codex_job.result,
            error_message=codex_job.error_message,
            created_at=codex_job.created_at,
            started_at=codex_job.started_at,
            finished_at=codex_job.finished_at,
        )
