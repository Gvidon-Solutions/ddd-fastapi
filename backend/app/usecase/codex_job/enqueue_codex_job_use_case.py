"""Provide the use case for enqueueing Codex jobs."""

from abc import ABC, abstractmethod

from app.domain.codex_job.entities import CodexJob
from app.domain.codex_job.repositories import CodexJobRepository
from app.domain.codex_job.value_objects import CodexJobPrompt
from app.usecase.codex_job.ports import CodexJobStarter


class EnqueueCodexJobUseCase(ABC):
    """Define the application boundary for enqueueing Codex jobs."""

    @abstractmethod
    async def execute(self, prompt: CodexJobPrompt) -> CodexJob:
        """Persist and enqueue a Codex job."""


class EnqueueCodexJobUseCaseImpl(EnqueueCodexJobUseCase):
    """Enqueue Codex jobs through a queue port."""

    def __init__(
        self,
        repository: CodexJobRepository,
        starter: CodexJobStarter,
    ):
        """Store use case dependencies."""
        self.repository = repository
        self.starter = starter

    async def execute(self, prompt: CodexJobPrompt) -> CodexJob:
        """Persist and enqueue a Codex job."""
        codex_job = CodexJob.create(prompt)
        await self.repository.save(codex_job)
        backend_job_id = await self.starter.start(codex_job.id)
        codex_job.attach_backend_job(backend_job_id)
        await self.repository.save(codex_job)
        return codex_job


def new_enqueue_codex_job_use_case(
    repository: CodexJobRepository,
    starter: CodexJobStarter,
) -> EnqueueCodexJobUseCase:
    """Instantiate the enqueue Codex job use case."""
    return EnqueueCodexJobUseCaseImpl(repository, starter)
