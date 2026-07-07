"""Define Codex auth transient session status."""

from __future__ import annotations

from enum import StrEnum


class CodexAuthSessionStatus(StrEnum):
    """Represent the transient Codex auth session state."""

    PENDING = "pending"
    AUTHENTICATED = "authenticated"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
