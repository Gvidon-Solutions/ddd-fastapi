"""Codex run job stage 4."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.domain.job.base.value_objects import JobStage


@dataclass(frozen=True)
class Stage4CodexRunCancelledData:
    """Represent cancelled Codex run stage data."""

    reason: str
    status: str = "cancelled"

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(frozen=True)
class Stage4CodexRunCancelled(JobStage):
    """Represent cancelled Codex run."""

    key: str = "codex_run"
    message: str | None = "Codex run cancelled"
    current: int | None = 4
    total: int | None = 4
    data: Stage4CodexRunCancelledData = field(
        default_factory=lambda: Stage4CodexRunCancelledData(reason="Job cancelled"),
    )
