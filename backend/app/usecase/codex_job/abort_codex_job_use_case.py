"""Provide the use case for aborting Codex jobs."""

from abc import ABC, abstractmethod

from app.domain.codex_job.entities import CodexJob
from app.domain.codex_job.exceptions import CodexJobNotFoundError
from app.domain.codex_job.repositories import CodexJobRepository
from app.domain.codex_job.value_objects import CodexJobId
from app.usecase.codex_job.ports import CodexJobStarter


class AbortCodexJobUseCase(ABC):
    """Define the application boundary for aborting Codex jobs."""

    @abstractmethod
    async def execute(self, codex_job_id: CodexJobId) -> CodexJob:
        """Abort a Codex job and return its state."""


class AbortCodexJobUseCaseImpl(AbortCodexJobUseCase):
    """Abort Codex jobs through a job queue port."""

    def __init__(
        self,
        repository: CodexJobRepository,
        starter: CodexJobStarter,
    ):
        """Store use case dependencies."""
        self.repository = repository
        self.starter = starter

    async def execute(self, codex_job_id: CodexJobId) -> CodexJob:
        """Abort a Codex job and return its state."""
        codex_job = await self.repository.find_by_id(codex_job_id)
        if codex_job is None:
            raise CodexJobNotFoundError
        if codex_job.backend_job_id is not None:
            await self.starter.abort(codex_job.backend_job_id)
        codex_job.abort()
        await self.repository.save(codex_job)
        return codex_job


def new_abort_codex_job_use_case(
    repository: CodexJobRepository,
    starter: CodexJobStarter,
) -> AbortCodexJobUseCase:
    """Instantiate the abort Codex job use case."""
    return AbortCodexJobUseCaseImpl(repository, starter)
