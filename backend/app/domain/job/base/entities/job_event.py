"""Define the JobEvent entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.job.base.value_objects import JobEventType


@dataclass
class JobEvent:
    """Represent a historical event emitted by a job."""

    id: UUID
    job_id: UUID
    type: JobEventType
    data: dict
    message: str | None
    created_at: datetime
