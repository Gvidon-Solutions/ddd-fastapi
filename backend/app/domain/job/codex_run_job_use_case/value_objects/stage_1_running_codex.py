"""Codex run job stage 1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.domain.job.base.value_objects import JobStage


@dataclass(frozen=True)
class Stage1RunningCodexData:
    """Represent running Codex stage data."""

    workdir: str
    status: str = "running"

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(frozen=True)
class Stage1RunningCodex(JobStage):
    """Represent running Codex."""

    key: str = "codex_run"
    message: str | None = "Running Codex"
    current: int | None = 1
    total: int | None = 3
    data: Stage1RunningCodexData = field(
        default_factory=lambda: Stage1RunningCodexData(workdir=""),
    )
