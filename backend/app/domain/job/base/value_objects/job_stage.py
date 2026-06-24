"""Define the JobStage value object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class JobStage:
    """Represent the current stage of a running job."""

    key: str
    message: str | None = None
    current: int | None = None
    total: int | None = None
    updated_at: datetime | None = None
    data: dict | None = None
