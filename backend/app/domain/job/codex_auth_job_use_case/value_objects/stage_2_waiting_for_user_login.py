"""Codex auth job stage 2."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.domain.job.base.value_objects import JobStage


@dataclass
class Stage2WaitingForUserLoginData:
    """Represent stage 2 data."""
    verification_url: str | None = None
    user_code: str | None = None
    device_code: str | None = None
    status: str = "waiting_for_user"

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(frozen=True)
class Stage2WaitingForUserLogin(JobStage):
    """Represent waiting for the user to complete Codex device auth."""

    key: str = "codex_auth"
    message: str | None = "Open verification URL and enter user code"
    current: int | None = 2
    total: int | None = 4
    data: Stage2WaitingForUserLoginData = field(
        default_factory=Stage2WaitingForUserLoginData,
    )
