"""Codex job runner port."""

from abc import ABC, abstractmethod

from app.domain.codex_job.entities import CodexJob


class CodexJobRunner(ABC):
    """Execute one Codex job."""

    @abstractmethod
    async def execute(self, codex_job: CodexJob) -> str:
        """Run a Codex job and return its result."""
