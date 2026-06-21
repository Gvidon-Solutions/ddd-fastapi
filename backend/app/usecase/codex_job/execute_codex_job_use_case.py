"""Provide the use case for executing queued Codex jobs."""

import asyncio
from abc import ABC, abstractmethod

from app.domain.codex_job.exceptions import CodexJobNotFoundError
from app.domain.codex_job.repositories import CodexJobRepository
from app.domain.codex_job.value_objects import CodexJobId
from app.usecase.codex_job.ports import CodexJobRunner


class ExecuteCodexJobUseCase(ABC):
    """Define the application boundary for executing Codex jobs."""

    @abstractmethod
    async def execute(self, codex_job_id: CodexJobId) -> str:
        """Execute a stored Codex job."""


class ExecuteCodexJobUseCaseImpl(ExecuteCodexJobUseCase):
    """Execute a stored Codex job with a runner port."""

    def __init__(
        self,
        repository: CodexJobRepository,
        runner: CodexJobRunner,
    ):
        """Store use case dependencies."""
        self.repository = repository
        self.runner = runner

    async def execute(self, codex_job_id: CodexJobId) -> str:
        """Execute a stored Codex job."""
        codex_job = await self.repository.find_by_id(codex_job_id)
        if codex_job is None:
            raise CodexJobNotFoundError

        try:
            codex_job.start()
            await self.repository.save(codex_job)
            result = await self.runner.execute(codex_job)
            codex_job.complete(result)
            await self.repository.save(codex_job)
        except asyncio.CancelledError:
            codex_job.abort()
            await self.repository.save(codex_job)
            raise
        except Exception as error:
            codex_job.fail(str(error))
            await self.repository.save(codex_job)
            raise

        return result


def new_execute_codex_job_use_case(
    repository: CodexJobRepository,
    runner: CodexJobRunner,
) -> ExecuteCodexJobUseCase:
    """Instantiate the execute Codex job use case."""
    return ExecuteCodexJobUseCaseImpl(repository, runner)
