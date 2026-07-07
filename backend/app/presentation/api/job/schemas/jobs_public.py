"""Paginated jobs response schema."""

from sqlmodel import SQLModel

from app.presentation.api.job.schemas.job_summary_public import JobSummaryPublic


class JobsPublic(SQLModel):
    """Paginated jobs response schema."""

    data: list[JobSummaryPublic]
    count: int
