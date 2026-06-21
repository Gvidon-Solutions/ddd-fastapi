"""Define the Codex job aggregate root."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.codex_job.value_objects import (
    CodexJobId,
    CodexJobPrompt,
    CodexJobStatus,
)


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


@dataclass(eq=False)
class CodexJob:
    """Represent an async backend job for a Codex workflow run."""

    id: CodexJobId
    prompt: CodexJobPrompt
    status: CodexJobStatus = CodexJobStatus.QUEUED
    backend_job_id: str | None = None
    result: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def __hash__(self) -> int:
        """Return a hash value based on the entity identity."""
        return hash(self.id)

    def __eq__(self, obj: object) -> bool:
        """Compare Codex jobs by identifier."""
        if isinstance(obj, CodexJob):
            return self.id == obj.id
        return False

    def attach_backend_job(self, backend_job_id: str) -> None:
        """Store the underlying backend queue job ID."""
        self.backend_job_id = backend_job_id

    def start(self) -> None:
        """Mark the job as running."""
        self.status = CodexJobStatus.RUNNING
        self.started_at = _utc_now()

    def complete(self, result: str) -> None:
        """Mark the job as succeeded."""
        self.status = CodexJobStatus.SUCCEEDED
        self.result = result
        self.error_message = None
        self.finished_at = _utc_now()

    def fail(self, error_message: str) -> None:
        """Mark the job as failed."""
        self.status = CodexJobStatus.FAILED
        self.error_message = error_message
        self.finished_at = _utc_now()

    def abort(self) -> None:
        """Mark the job as aborted."""
        self.status = CodexJobStatus.ABORTED
        self.finished_at = _utc_now()

    @staticmethod
    def create(prompt: CodexJobPrompt) -> "CodexJob":
        """Create a queued Codex job."""
        return CodexJob(id=CodexJobId.generate(), prompt=prompt)
