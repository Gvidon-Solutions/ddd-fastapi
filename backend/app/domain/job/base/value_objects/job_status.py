"""Define job statuses."""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    """Represent the lifecycle state of a job."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
