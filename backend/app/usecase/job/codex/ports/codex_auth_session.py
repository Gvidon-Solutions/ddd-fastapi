"""Codex auth transient session port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class CodexAuthSessionStatus(StrEnum):
    """Represent the transient Codex auth session state."""

    PENDING = "pending"
    AUTHENTICATED = "authenticated"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass(frozen=True)
class CodexAuthSession:
    """Transient Codex auth polling data."""

    job_id: UUID
    verification_url: str | None
    user_code: str | None
    expires_at: datetime
    status: CodexAuthSessionStatus
    error: str | None
    created_at: datetime
    updated_at: datetime


class CodexAuthSessionStore(ABC):
    """Store transient Codex auth sessions outside durable job state."""

    @abstractmethod
    async def save_pending(
        self,
        *,
        job_id: UUID,
        verification_url: str | None,
        user_code: str | None,
        expires_at: datetime,
    ) -> None:
        """Persist pending login data."""

    @abstractmethod
    async def mark_authenticated(self, job_id: UUID) -> None:
        """Mark the session authenticated and clear sensitive fields."""

    @abstractmethod
    async def mark_failed(self, job_id: UUID, error: str) -> None:
        """Mark the session failed and clear sensitive fields."""

    @abstractmethod
    async def mark_cancelled(self, job_id: UUID, reason: str) -> None:
        """Mark the session cancelled and clear sensitive fields."""

    @abstractmethod
    async def get(self, job_id: UUID) -> CodexAuthSession | None:
        """Return a transient session when one exists."""
