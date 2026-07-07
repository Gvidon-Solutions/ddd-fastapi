"""Codex auth ARQ task."""

from __future__ import annotations

from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job.codex_auth_job_use_case import CodexAuthJobV1, CodexAuthResult
from app.infrastructure.arq.deps import (
    ARQ_CODEX_AUTH_SESSION_REPOSITORY,
    ARQ_CODEX_AUTHENTICATOR,
    get_arq_db_engine,
    new_arq_job_repository,
)
from app.infrastructure.arq.job_workers import job_worker
from app.usecase.job.codex import new_codex_auth_use_case


@job_worker
async def execute_codex_auth_job_use_case(
    ctx: dict[str, Any],
    job: CodexAuthJobV1,
) -> CodexAuthResult:
    """Run Codex device auth for one persisted job."""
    engine = get_arq_db_engine(ctx)
    async with AsyncSession(engine) as session:
        jobs = new_arq_job_repository(session)
        use_case = new_codex_auth_use_case(
            jobs=jobs,
            codex_authenticator=ctx[ARQ_CODEX_AUTHENTICATOR],
            auth_sessions=ctx[ARQ_CODEX_AUTH_SESSION_REPOSITORY],
        )
        return await use_case.execute(job)
