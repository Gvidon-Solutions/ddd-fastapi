"""Codex job repository contract."""

from abc import ABC, abstractmethod

from app.domain.codex_job.entities import CodexJob
from app.domain.codex_job.value_objects import CodexJobId


class CodexJobRepository(ABC):
    """Persist Codex jobs."""

    @abstractmethod
    async def save(self, codex_job: CodexJob) -> None:
        """Insert or update a Codex job."""

    @abstractmethod
    async def find_by_id(self, codex_job_id: CodexJobId) -> CodexJob | None:
        """Return a Codex job by ID."""
