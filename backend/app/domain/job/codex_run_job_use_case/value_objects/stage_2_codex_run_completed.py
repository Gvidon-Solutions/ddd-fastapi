"""Codex run job stage 2."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.domain.job.base.value_objects import JobStage


@dataclass(frozen=True)
class Stage2CodexRunCompletedData:
    """Represent completed Codex run stage data."""

    output_artifact_id: str | None
    log_artifacts: int
    generated_artifacts: int
    status: str = "succeeded"

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(frozen=True)
class Stage2CodexRunCompleted(JobStage):
    """Represent completed Codex run."""

    key: str = "codex_run"
    message: str | None = "Codex finished"
    current: int | None = 2
    total: int | None = 3
    data: Stage2CodexRunCompletedData = field(
        default_factory=lambda: Stage2CodexRunCompletedData(
            output_artifact_id=None,
            log_artifacts=0,
            generated_artifacts=0,
        ),
    )
