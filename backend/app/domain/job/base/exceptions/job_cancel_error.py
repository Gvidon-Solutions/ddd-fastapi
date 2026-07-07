"""Base job cancellation error."""

from __future__ import annotations


class JobCancelError(Exception):
    """Base class for job cancellation errors."""

    detail = "Job cancellation error."

    def __init__(self, detail: str | None = None) -> None:
        """Create an error with default or custom detail."""
        self.detail = detail or self.detail
        super().__init__(self.detail)
