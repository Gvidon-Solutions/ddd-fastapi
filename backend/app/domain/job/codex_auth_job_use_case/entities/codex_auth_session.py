"""Define Codex auth transient session entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.job.codex_auth_job_use_case.value_objects.codex_auth_session_status import (
    CodexAuthSessionStatus,
)


@dataclass
class CodexAuthSession:
    """Transient Codex auth polling session."""

    job_id: UUID
    verification_url: str | None
    user_code: str | None
    expires_at: datetime
    status: CodexAuthSessionStatus
    error: str | None
    created_at: datetime
    updated_at: datetime
