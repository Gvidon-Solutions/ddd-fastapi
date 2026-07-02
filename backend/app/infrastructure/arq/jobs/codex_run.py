"""Codex run ARQ task."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.domain.job import JobRepository
from app.domain.job.codex_run_job_use_case import CodexRunJobV1
from app.infrastructure.arq.deps import (
    ARQ_ARTIFACT_STORAGE,
    get_arq_db_engine,
    new_arq_job_artifact_repository,
    new_arq_job_event_repository,
    new_arq_job_repository,
)
from app.infrastructure.arq.job_workers import job_worker
from app.infrastructure.codex import new_codex_executor
from app.usecase.job.codex import new_codex_run_job_use_case


@job_worker(contract=CodexRunJobV1)
async def codex_run(
    ctx: dict[str, Any],
    job_id: str,
) -> dict:
    """Run Codex exec for one persisted job."""
    engine = get_arq_db_engine(ctx)
    async with AsyncSession(engine) as session:
        try:
            jobs = new_arq_job_repository(session)
            if not await _claim_execution(jobs, UUID(job_id)):
                return {}
            use_case = new_codex_run_job_use_case(
                jobs=jobs,
                artifacts=new_arq_job_artifact_repository(session),
                storage=ctx[ARQ_ARTIFACT_STORAGE],
                job_events=new_arq_job_event_repository(session),
                codex_executor=new_codex_executor(),
                default_working_directory=Path(settings.CODEX_JOB_WORKING_DIRECTORY),
            )
            return await use_case.execute(UUID(job_id))
        except Exception:
            await session.rollback()
            raise


async def _claim_execution(jobs: JobRepository, job_id: UUID) -> bool:
    try:
        from datetime import UTC, datetime

        return await jobs.try_mark_running(job_id, started_at=datetime.now(UTC))
    except NotImplementedError:
        return True
