"""Codex auth job stage 1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.domain.job.base.value_objects import JobStage


@dataclass(frozen=True)
class Stage1StartingCodexDeviceAuthData:
    """Represent stage 1 data."""
    status: str = "starting"

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(frozen=True)
class Stage1StartingCodexDeviceAuth(JobStage):
    """Represent starting Codex device auth."""

    key: str = "codex_auth"
    message: str | None = "Starting Codex device auth"
    current: int | None = 1
    total: int | None = 4
    data: Stage1StartingCodexDeviceAuthData = field(
        default_factory=Stage1StartingCodexDeviceAuthData,
    )
