"""Define the Codex auth session repository contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.job import JobId
from app.domain.job.codex_auth_job_use_case.entities import CodexAuthSession


class CodexAuthSessionRepository(ABC):
    """Persist transient Codex auth sessions."""

    @abstractmethod
    async def save_pending(
        self,
        *,
        job_id: JobId,
        verification_url: str | None,
        user_code: str | None,
        expires_at: datetime,
    ) -> None:
        """Persist pending login data."""

    @abstractmethod
    async def mark_authenticated(self, job_id: JobId) -> None:
        """Mark the session authenticated and clear sensitive fields."""

    @abstractmethod
    async def mark_failed(self, job_id: JobId, error: str) -> None:
        """Mark the session failed and clear sensitive fields."""

    @abstractmethod
    async def mark_cancelled(self, job_id: JobId, reason: str) -> None:
        """Mark the session cancelled and clear sensitive fields."""

    @abstractmethod
    async def get(self, job_id: JobId) -> CodexAuthSession | None:
        """Return a transient session when one exists."""
