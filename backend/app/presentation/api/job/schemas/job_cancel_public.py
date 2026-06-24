"""Job cancellation response schema."""

from uuid import UUID

from sqlmodel import SQLModel


class JobCancelPublic(SQLModel):
    """Response returned after a cancel request."""

    job_id: UUID
    cancelled: bool
