"""Base job contract error."""

from __future__ import annotations


class JobContractError(Exception):
    """Base class for job contract errors."""

    detail = "Job contract error."

    def __init__(self, detail: str | None = None) -> None:
        """Create an error with default or custom detail."""
        self.detail = detail or self.detail
        super().__init__(self.detail)
