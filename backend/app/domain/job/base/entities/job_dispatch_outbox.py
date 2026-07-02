"""Job dispatch outbox entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class JobDispatchOutboxStatus(StrEnum):
    """Represent durable dispatch intent status."""

    PENDING = "pending"
    DISPATCHED = "dispatched"
    FAILED = "failed"


@dataclass(frozen=True)
class JobDispatchOutbox:
    """Represent one durable request to dispatch a job."""

    outbox_id: UUID
    job_id: UUID
    type: str
    version: str
    status: JobDispatchOutboxStatus
    attempts: int
    next_attempt_at: datetime
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    dispatched_at: datetime | None
