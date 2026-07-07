"""Base job creation error."""

from __future__ import annotations


class JobCreateError(Exception):
    """Base class for job creation errors."""

    detail = "Job creation error."

    def __init__(self, detail: str | None = None) -> None:
        """Create an error with default or custom detail."""
        self.detail = detail or self.detail
        super().__init__(self.detail)
