"""ARQ worker configuration."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.infrastructure.arq.deps import (
    ARQ_ARTIFACT_STORAGE,
    ARQ_CLOCK,
    ARQ_CODEX_AUTHENTICATOR,
    ARQ_DB_ENGINE,
)
from app.infrastructure.arq.jobs import execute_codex_auth_job_use_case, codex_run
from app.infrastructure.arq.settings import arq_redis_settings
from app.infrastructure.artifact_storage import new_filesystem_artifact_storage
from app.infrastructure.clock import new_system_clock
from app.infrastructure.codex import new_codex_authenticator


async def on_startup(ctx: dict[str, Any]) -> None:
    """Initialize ARQ worker dependencies."""
    ctx[ARQ_DB_ENGINE] = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    ctx[ARQ_ARTIFACT_STORAGE] = new_filesystem_artifact_storage()
    ctx[ARQ_CLOCK] = new_system_clock()
    ctx[ARQ_CODEX_AUTHENTICATOR] = new_codex_authenticator()


async def on_shutdown(ctx: dict[str, Any]) -> None:
    """Dispose ARQ worker dependencies."""
    engine = ctx.get(ARQ_DB_ENGINE)
    if engine is not None:
        await engine.dispose()


class WorkerSettings:
    """Configure the ARQ worker process."""

    functions = [execute_codex_auth_job_use_case, codex_run]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = arq_redis_settings()
    queue_name = settings.ARQ_QUEUE_NAME
    job_timeout = settings.ARQ_JOB_TIMEOUT_SECONDS
    keep_result = settings.ARQ_RESULT_TTL_SECONDS
    allow_abort_jobs = True
