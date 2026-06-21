"""Define Codex job statuses."""

from enum import StrEnum


class CodexJobStatus(StrEnum):
    """Represent the lifecycle state of an async Codex job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABORTED = "aborted"
