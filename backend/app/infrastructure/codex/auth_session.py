"""Redis-backed Codex auth session store."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from arq.connections import ArqRedis, create_pool

from app.config import settings
from app.infrastructure.arq.settings import arq_redis_settings
from app.usecase.job.codex import (
    CodexAuthSession,
    CodexAuthSessionStatus,
    CodexAuthSessionStore,
)


class RedisCodexAuthSessionStore(CodexAuthSessionStore):
    """Store Codex auth sessions in Redis."""

    def __init__(
        self,
        redis: Any | None = None,
        *,
        pending_ttl_seconds: int = settings.CODEX_AUTH_SESSION_PENDING_TTL_SECONDS,
        terminal_ttl_seconds: int = settings.CODEX_AUTH_SESSION_TERMINAL_TTL_SECONDS,
    ) -> None:
        """Store Redis dependencies and TTL settings."""
        self.redis = redis
        self.pending_ttl_seconds = pending_ttl_seconds
        self.terminal_ttl_seconds = terminal_ttl_seconds

    async def save_pending(
        self,
        *,
        job_id: UUID,
        verification_url: str | None,
        user_code: str | None,
        expires_at: datetime,
    ) -> None:
        """Persist pending login data."""
        now = _now()
        session = CodexAuthSession(
            job_id=job_id,
            verification_url=verification_url,
            user_code=user_code,
            expires_at=expires_at,
            status=CodexAuthSessionStatus.PENDING,
            error=None,
            created_at=now,
            updated_at=now,
        )
        ttl = max(1, int((expires_at - now).total_seconds()))
        await self._set(job_id, session, ttl=min(ttl, self.pending_ttl_seconds))

    async def mark_authenticated(self, job_id: UUID) -> None:
        """Mark the session authenticated and clear sensitive fields."""
        await self._mark_terminal(
            job_id,
            status=CodexAuthSessionStatus.AUTHENTICATED,
            error=None,
        )

    async def mark_failed(self, job_id: UUID, error: str) -> None:
        """Mark the session failed and clear sensitive fields."""
        await self._mark_terminal(
            job_id,
            status=CodexAuthSessionStatus.FAILED,
            error=error,
        )

    async def mark_cancelled(self, job_id: UUID, reason: str) -> None:
        """Mark the session cancelled and clear sensitive fields."""
        await self._mark_terminal(
            job_id,
            status=CodexAuthSessionStatus.CANCELLED,
            error=reason,
        )

    async def get(self, job_id: UUID) -> CodexAuthSession | None:
        """Return a transient session when one exists."""
        if self.redis is not None:
            return await self._get(self.redis, job_id)
        async with self._redis_pool() as redis:
            return await self._get(redis, job_id)

    async def _mark_terminal(
        self,
        job_id: UUID,
        *,
        status: CodexAuthSessionStatus,
        error: str | None,
    ) -> None:
        existing = await self.get(job_id)
        now = _now()
        session = CodexAuthSession(
            job_id=job_id,
            verification_url=None,
            user_code=None,
            expires_at=existing.expires_at if existing is not None else now,
            status=status,
            error=error,
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
        )
        await self._set(job_id, session, ttl=self.terminal_ttl_seconds)

    async def _set(
        self,
        job_id: UUID,
        session: CodexAuthSession,
        *,
        ttl: int,
    ) -> None:
        payload = json.dumps(_session_to_record(session))
        if self.redis is not None:
            await self.redis.set(_key(job_id), payload, ex=ttl)
            return
        async with self._redis_pool() as redis:
            await redis.set(_key(job_id), payload, ex=ttl)

    async def _get(self, redis: Any, job_id: UUID) -> CodexAuthSession | None:
        payload = await redis.get(_key(job_id))
        if payload is None:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode()
        return _session_from_record(json.loads(payload))

    @asynccontextmanager
    async def _redis_pool(self) -> AsyncIterator[ArqRedis]:
        """Open and close a Redis pool."""
        redis = await create_pool(arq_redis_settings())
        try:
            yield redis
        finally:
            await redis.aclose()


def _key(job_id: UUID) -> str:
    return f"codex_auth_session:{job_id}"


def _now() -> datetime:
    return datetime.now(UTC)


def _session_to_record(session: CodexAuthSession) -> dict[str, str | None]:
    return {
        "job_id": str(session.job_id),
        "verification_url": session.verification_url,
        "user_code": session.user_code,
        "expires_at": session.expires_at.isoformat(),
        "status": session.status.value,
        "error": session.error,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


def _session_from_record(record: dict) -> CodexAuthSession:
    return CodexAuthSession(
        job_id=UUID(record["job_id"]),
        verification_url=record.get("verification_url"),
        user_code=record.get("user_code"),
        expires_at=datetime.fromisoformat(record["expires_at"]),
        status=CodexAuthSessionStatus(record["status"]),
        error=record.get("error"),
        created_at=datetime.fromisoformat(record["created_at"]),
        updated_at=datetime.fromisoformat(record["updated_at"]),
    )


def new_redis_codex_auth_session_store() -> CodexAuthSessionStore:
    """Create a Redis-backed Codex auth session store."""
    return RedisCodexAuthSessionStore()
