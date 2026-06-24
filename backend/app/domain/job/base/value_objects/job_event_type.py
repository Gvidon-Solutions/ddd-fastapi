"""Define job event types."""

from __future__ import annotations

from enum import StrEnum


class JobEventType(StrEnum):
    """Represent an event in the job execution history."""

    STARTED = "started"
    STAGE_CHANGED = "stage_changed"
    ARTIFACT_CREATED = "artifact_created"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
