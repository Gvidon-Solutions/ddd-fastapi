"""Base job restart error."""

from __future__ import annotations


class JobRestartError(Exception):
    """Base class for job restart errors."""

    detail = "Job restart error."

    def __init__(self, detail: str | None = None) -> None:
        """Create an error with default or custom detail."""
        self.detail = detail or self.detail
        super().__init__(self.detail)
