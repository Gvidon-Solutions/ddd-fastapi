"""Codex device login response schema."""

from uuid import UUID

from pydantic import BaseModel


class CodexDeviceLogin(BaseModel):
    """Describe one Codex device login session."""

    session_id: UUID
    status: str
    verification_url: str | None = None
    user_code: str | None = None
    raw_output: str
    return_code: int | None = None
