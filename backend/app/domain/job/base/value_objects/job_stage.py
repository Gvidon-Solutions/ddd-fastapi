"""Define the JobStage value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobStage:
    """Represent the current stage of a running job."""

    key: str
    message: str | None = None
    current: int | None = None
    total: int | None = None
    data: dict | None = None
