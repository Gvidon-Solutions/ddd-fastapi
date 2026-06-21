"""Define the Codex device login session entity."""

from dataclasses import dataclass
from uuid import UUID

from app.domain.agent.value_objects import CodexDeviceLoginStatus


@dataclass(frozen=True)
class CodexDeviceLoginSession:
    """Represent a Codex CLI device-code authentication session."""

    id: UUID
    status: CodexDeviceLoginStatus
    verification_url: str | None = None
    user_code: str | None = None
    raw_output: str = ""
    return_code: int | None = None
