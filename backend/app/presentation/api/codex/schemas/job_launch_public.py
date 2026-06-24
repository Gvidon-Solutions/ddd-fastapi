"""Codex job launch response schema."""

from uuid import UUID

from sqlmodel import SQLModel


class JobLaunchPublic(SQLModel):
    """Response returned after a job is queued."""

    job_id: UUID
