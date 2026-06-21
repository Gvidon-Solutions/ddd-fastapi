"""ARQ worker configuration for Codex jobs."""

import asyncio
from typing import Annotated, Any
from uuid import UUID

from fast_depends import Depends, inject

from app.config import settings
from app.domain.codex_job.exceptions import CodexJobNotFoundError
from app.domain.codex_job.value_objects import CodexJobId
from app.infrastructure.arq.deps import (
    CodexJobWorkerDependencies,
    get_codex_job_worker_dependencies,
)
from app.infrastructure.arq.settings import arq_redis_settings


@inject
async def run_codex_job(
    _ctx: dict[str, Any],
    codex_job_id: str,
    dependencies: Annotated[
        CodexJobWorkerDependencies,
        Depends(get_codex_job_worker_dependencies),
    ],
) -> str:
    """Execute one persisted Codex job."""
    parsed_codex_job_id = CodexJobId(UUID(codex_job_id))
    session = dependencies.session
    repository = dependencies.repository
    runner = dependencies.runner
    codex_job = await repository.find_by_id(parsed_codex_job_id)
    if codex_job is None:
        raise CodexJobNotFoundError

    try:
        codex_job.start()
        await repository.save(codex_job)
        await session.commit()

        result = await runner.execute(codex_job)
        codex_job.complete(result)
        await repository.save(codex_job)
        await session.commit()
    except asyncio.CancelledError:
        await session.rollback()
        codex_job.abort()
        await repository.save(codex_job)
        await session.commit()
        raise
    except Exception as error:
        await session.rollback()
        codex_job.fail(str(error))
        await repository.save(codex_job)
        await session.commit()
        raise

    return result


class WorkerSettings:
    """Configure the ARQ worker process."""

    functions = [run_codex_job]
    redis_settings = arq_redis_settings()
    queue_name = settings.ARQ_QUEUE_NAME
    job_timeout = settings.ARQ_JOB_TIMEOUT_SECONDS
    keep_result = settings.ARQ_RESULT_TTL_SECONDS
    allow_abort_jobs = True
