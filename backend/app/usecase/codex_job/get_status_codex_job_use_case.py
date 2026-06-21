"""Provide the use case for reading Codex job status."""

from abc import ABC, abstractmethod

from app.domain.codex_job.entities import CodexJob
from app.domain.codex_job.exceptions import CodexJobNotFoundError
from app.domain.codex_job.repositories import CodexJobRepository
from app.domain.codex_job.value_objects import CodexJobId


class GetStatusCodexJobUseCase(ABC):
    """Define the application boundary for reading Codex job status."""

    @abstractmethod
    async def execute(self, codex_job_id: CodexJobId) -> CodexJob:
        """Return the current state of a Codex job."""


class GetStatusCodexJobUseCaseImpl(GetStatusCodexJobUseCase):
    """Read Codex job status through a job queue port."""

    def __init__(self, repository: CodexJobRepository):
        """Store use case dependencies."""
        self.repository = repository

    async def execute(self, codex_job_id: CodexJobId) -> CodexJob:
        """Return the current state of a Codex job."""
        codex_job = await self.repository.find_by_id(codex_job_id)
        if codex_job is None:
            raise CodexJobNotFoundError
        return codex_job


def new_get_status_codex_job_use_case(
    repository: CodexJobRepository,
) -> GetStatusCodexJobUseCase:
    """Instantiate the get Codex job status use case."""
    return GetStatusCodexJobUseCaseImpl(repository)
