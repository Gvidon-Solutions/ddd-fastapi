"""Define the JobError value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobError:
    """Represent a job failure."""

    code: str
    message: str
    details: dict | None = None
