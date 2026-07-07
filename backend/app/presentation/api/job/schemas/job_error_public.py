"""Job error response schema."""

from sqlmodel import SQLModel

from app.domain.job import JobError


class JobErrorPublic(SQLModel):
    """Job error response schema."""

    code: str
    message: str
    details: dict
    retryable: bool

    @classmethod
    def from_value_object(cls, error: JobError) -> "JobErrorPublic":
        """Build an API response from a domain value object."""
        return cls(
            code=error.code,
            message=error.message,
            details=error.details,
            retryable=error.retryable,
        )
