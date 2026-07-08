"""Codex run ARQ task."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.domain.job.codex_run_job_use_case import CodexRunJobV1, CodexRunOutput
from app.infrastructure.arq.deps import (
    ARQ_FILE_STORAGE,
    ARQ_REDIS,
    get_arq_db_engine,
    new_arq_job_repository,
)
from app.infrastructure.arq.job_event_publisher import new_redis_event_publisher
from app.infrastructure.arq.job_workers import job_worker
from app.infrastructure.codex import new_codex_executor
from app.usecase.job.codex import new_codex_run_job_use_case


@job_worker
async def execute_codex_run_job_use_case(
    ctx: dict[str, Any],
    job: CodexRunJobV1,
) -> CodexRunOutput:
    """Run Codex exec for one persisted job."""
    engine = get_arq_db_engine(ctx)
    async with AsyncSession(engine) as session:
        jobs = new_arq_job_repository(session)
        use_case = new_codex_run_job_use_case(
            jobs=jobs,
            storage=ctx[ARQ_FILE_STORAGE],
            codex_executor=new_codex_executor(),
            default_working_directory=Path(settings.CODEX_JOB_WORKING_DIRECTORY),
            event_publisher=new_redis_event_publisher(ctx[ARQ_REDIS]),
        )
        return await use_case.execute(job)
