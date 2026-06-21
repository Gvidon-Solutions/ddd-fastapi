"""Codex job starter port."""

from abc import ABC, abstractmethod

from app.domain.codex_job.value_objects import CodexJobId


class CodexJobStarter(ABC):
    """Start and abort backend Codex jobs."""

    @abstractmethod
    async def start(self, codex_job_id: CodexJobId) -> str:
        """Start a backend Codex job and return backend job ID."""

    @abstractmethod
    async def abort(self, backend_job_id: str) -> None:
        """Abort a backend Codex job."""
