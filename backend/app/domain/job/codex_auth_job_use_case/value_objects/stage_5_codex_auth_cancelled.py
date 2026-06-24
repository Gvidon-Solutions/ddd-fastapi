"""Codex auth job stage 5."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.domain.job.base.value_objects import JobStage


@dataclass(frozen=True)
class Stage5CodexAuthCancelledData:
    """Represent cancelled Codex auth stage data."""

    reason: str
    status: str = "cancelled"

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(frozen=True)
class Stage5CodexAuthCancelled(JobStage):
    """Represent cancelled Codex auth."""

    key: str = "codex_auth"
    message: str | None = "Codex auth cancelled"
    current: int | None = 5
    total: int | None = 5
    data: Stage5CodexAuthCancelledData = field(
        default_factory=lambda: Stage5CodexAuthCancelledData(reason="Job cancelled"),
    )
