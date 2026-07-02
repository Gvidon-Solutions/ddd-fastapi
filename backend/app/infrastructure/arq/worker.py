"""ARQ worker configuration."""

from __future__ import annotations

import importlib
from typing import Any

from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.infrastructure.arq.deps import (
    ARQ_CODEX_AUTH_SESSION,
    ARQ_CODEX_AUTHENTICATOR,
    ARQ_DB_ENGINE,
    ARQ_FILE_STORAGE,
)
from app.infrastructure.arq.job_workers import worker_bindings
from app.infrastructure.arq.settings import arq_redis_settings
from app.infrastructure.codex import (
    new_codex_authenticator,
    new_redis_codex_auth_session_store,
)
from app.infrastructure.file_storage import new_filesystem_file_storage

importlib.import_module("app.infrastructure.arq.jobs")


async def on_startup(ctx: dict[str, Any]) -> None:
    """Initialize ARQ worker dependencies."""
    ctx[ARQ_DB_ENGINE] = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    ctx[ARQ_FILE_STORAGE] = new_filesystem_file_storage()
    ctx[ARQ_CODEX_AUTHENTICATOR] = new_codex_authenticator()
    ctx[ARQ_CODEX_AUTH_SESSION] = new_redis_codex_auth_session_store()


async def on_shutdown(ctx: dict[str, Any]) -> None:
    """Dispose ARQ worker dependencies."""
    engine = ctx.get(ARQ_DB_ENGINE)
    if engine is not None:
        await engine.dispose()


class WorkerSettings:
    """Configure the ARQ worker process."""

    functions = worker_bindings.functions()
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = arq_redis_settings()
    queue_name = settings.ARQ_QUEUE_NAME
    job_timeout = settings.ARQ_JOB_TIMEOUT_SECONDS
    keep_result = settings.ARQ_RESULT_TTL_SECONDS
    allow_abort_jobs = True
