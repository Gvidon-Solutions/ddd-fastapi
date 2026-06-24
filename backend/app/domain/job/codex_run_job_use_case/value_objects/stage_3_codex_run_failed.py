"""Codex run job stage 3."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.domain.job.base.value_objects import JobStage


@dataclass(frozen=True)
class Stage3CodexRunFailedData:
    """Represent failed Codex run stage data."""

    error: str
    status: str = "failed"

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(frozen=True)
class Stage3CodexRunFailed(JobStage):
    """Represent failed Codex run."""

    key: str = "codex_run"
    message: str | None = "Codex failed"
    current: int | None = 3
    total: int | None = 3
    data: Stage3CodexRunFailedData = field(
        default_factory=lambda: Stage3CodexRunFailedData(error=""),
    )
