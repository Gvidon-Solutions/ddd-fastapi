"""Job error response schema."""

from sqlmodel import SQLModel

from app.domain.job import JobError


class JobErrorPublic(SQLModel):
    """Job error response schema."""

    code: str
    message: str
    details: dict
    retryable: bool

    @staticmethod
    def from_value_object(error: JobError) -> "JobErrorPublic":
        """Build an API response from a domain value object."""
        return JobErrorPublic(
            code=error.code,
            message=error.message,
            details=error.details,
            retryable=error.retryable,
        )
