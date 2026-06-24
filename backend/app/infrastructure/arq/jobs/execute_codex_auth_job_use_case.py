"""Codex auth ARQ task."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.infrastructure.arq.deps import (
    ARQ_CODEX_AUTHENTICATOR,
    get_arq_db_engine,
    new_arq_job_event_repository,
    new_arq_job_repository,
)
from app.usecase.job.codex import new_codex_auth_use_case


async def execute_codex_auth_job_use_case(
    ctx: dict[str, Any],
    job_id: str,
) -> dict:
    """Run Codex device auth for one persisted job."""
    engine = get_arq_db_engine(ctx)
    async with AsyncSession(engine) as session:
        try:
            use_case = new_codex_auth_use_case(
                jobs=new_arq_job_repository(session),
                job_events=new_arq_job_event_repository(session),
                codex_authenticator=ctx[ARQ_CODEX_AUTHENTICATOR],
            )
            return (await use_case.execute(UUID(job_id))).to_dict()
        except Exception:
            await session.rollback()
            raise
