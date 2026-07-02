"""Codex auth ARQ task."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import JobRepository
from app.domain.job.codex_auth_job_use_case import CodexAuthJobV1
from app.infrastructure.arq.deps import (
    ARQ_CODEX_AUTH_SESSION,
    ARQ_CODEX_AUTHENTICATOR,
    get_arq_db_engine,
    new_arq_job_event_repository,
    new_arq_job_repository,
)
from app.infrastructure.arq.job_workers import job_worker
from app.usecase.job.codex import new_codex_auth_use_case


@job_worker(contract=CodexAuthJobV1)
async def execute_codex_auth_job_use_case(
    ctx: dict[str, Any],
    job_id: str,
) -> dict:
    """Run Codex device auth for one persisted job."""
    engine = get_arq_db_engine(ctx)
    async with AsyncSession(engine) as session:
        try:
            jobs = new_arq_job_repository(session)
            if not await _claim_execution(jobs, UUID(job_id)):
                return {}
            use_case = new_codex_auth_use_case(
                jobs=jobs,
                job_events=new_arq_job_event_repository(session),
                codex_authenticator=ctx[ARQ_CODEX_AUTHENTICATOR],
                auth_sessions=ctx[ARQ_CODEX_AUTH_SESSION],
            )
            return (await use_case.execute(UUID(job_id))).to_dict()
        except Exception:
            await session.rollback()
            raise


async def _claim_execution(jobs: JobRepository, job_id: UUID) -> bool:
    try:
        from datetime import UTC, datetime

        return await jobs.try_mark_running(job_id, started_at=datetime.now(UTC))
    except NotImplementedError:
        return True
