"""Codex auth job stage 4."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.domain.job.base.value_objects import JobStage


@dataclass(frozen=True)
class Stage4CodexAuthFailedData:
    """Represent stage 4 data."""
    error: str
    status: str = "failed"

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(frozen=True)
class Stage4CodexAuthFailed(JobStage):
    """Represent failed Codex device auth."""

    key: str = "codex_auth"
    message: str | None = "Codex auth failed"
    current: int | None = 4
    total: int | None = 4
    data: Stage4CodexAuthFailedData = field(
        default_factory=lambda: Stage4CodexAuthFailedData(error=""),
    )
