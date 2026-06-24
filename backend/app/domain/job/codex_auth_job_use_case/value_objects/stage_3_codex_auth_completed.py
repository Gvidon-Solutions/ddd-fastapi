"""Codex auth job stage 3."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.domain.job.base.value_objects import JobStage


@dataclass
class Stage3CodexAuthCompletedData:
    """Represent stage 3 data."""
    authenticated: bool
    verification_url: str | None = None
    device_code: str | None = None
    error_message: str | None = None
    status: str = "authenticated"

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(frozen=True)
class Stage3CodexAuthCompleted(JobStage):
    """Represent completed Codex device auth."""

    key: str = "codex_auth"
    message: str | None = "Codex auth completed"
    current: int | None = 3
    total: int | None = 4
    data: Stage3CodexAuthCompletedData = field(
        default_factory=lambda: Stage3CodexAuthCompletedData(authenticated=True),
    )
