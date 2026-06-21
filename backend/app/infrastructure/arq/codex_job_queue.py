"""ARQ implementation of the Codex job starter port."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from arq.connections import ArqRedis, create_pool
from arq.jobs import Job

from app.config import settings
from app.domain.codex_job.value_objects import CodexJobId
from app.infrastructure.arq.settings import arq_redis_settings
from app.usecase.codex_job import CodexJobStarter


class ArqCodexJobStarter(CodexJobStarter):
    """Manage Codex jobs through ARQ."""

    async def start(self, codex_job_id: CodexJobId) -> str:
        """Enqueue a Codex job and return its ARQ job ID."""
        async with self._redis_pool() as redis:
            job = await redis.enqueue_job(
                "run_codex_job",
                str(codex_job_id.value),
                _queue_name=settings.ARQ_QUEUE_NAME,
            )
            if job is None:
                raise RuntimeError("Codex job was not enqueued")
            return job.job_id

    async def abort(self, backend_job_id: str) -> None:
        """Abort an ARQ Codex job."""
        async with self._redis_pool() as redis:
            job = Job(backend_job_id, redis=redis, _queue_name=settings.ARQ_QUEUE_NAME)
            await job.abort(timeout=0)

    @asynccontextmanager
    async def _redis_pool(self) -> AsyncIterator[ArqRedis]:
        """Open and close an ARQ Redis pool."""
        redis = await create_pool(
            arq_redis_settings(),
            default_queue_name=settings.ARQ_QUEUE_NAME,
        )
        try:
            yield redis
        finally:
            await redis.aclose()


def new_codex_job_starter() -> CodexJobStarter:
    """Create a Codex job starter."""
    return ArqCodexJobStarter()
