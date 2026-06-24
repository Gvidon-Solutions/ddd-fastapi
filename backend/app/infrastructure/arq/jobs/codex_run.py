"""Codex run ARQ task."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.infrastructure.arq.deps import (
    ARQ_ARTIFACT_STORAGE,
    get_arq_db_engine,
    new_arq_job_artifact_repository,
    new_arq_job_event_repository,
    new_arq_job_repository,
)
from app.infrastructure.codex import new_codex_executor
from app.usecase.job.codex import new_codex_run_job_use_case


async def codex_run(
    ctx: dict[str, Any],
    job_id: str,
) -> dict:
    """Run Codex exec for one persisted job."""
    engine = get_arq_db_engine(ctx)
    async with AsyncSession(engine) as session:
        try:
            use_case = new_codex_run_job_use_case(
                jobs=new_arq_job_repository(session),
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
