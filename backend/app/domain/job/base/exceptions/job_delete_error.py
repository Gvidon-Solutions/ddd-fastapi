"""Base job deletion error."""

from __future__ import annotations


class JobDeleteError(Exception):
    """Base class for job deletion errors."""

    detail = "Job deletion error."

    def __init__(self, detail: str | None = None) -> None:
        """Create an error with default or custom detail."""
        self.detail = detail or self.detail
        super().__init__(self.detail)
