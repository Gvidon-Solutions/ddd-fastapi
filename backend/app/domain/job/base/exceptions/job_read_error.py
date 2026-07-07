"""Base job read error."""

from __future__ import annotations


class JobReadError(Exception):
    """Raised when a job read operation fails."""

    detail = "Job read error."
