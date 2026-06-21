"""Define Codex device login statuses."""

from enum import StrEnum


class CodexDeviceLoginStatus(StrEnum):
    """Represent the lifecycle state of a Codex device login session."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
