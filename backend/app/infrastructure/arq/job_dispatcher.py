"""Dispatch pending jobs from ARQ cron."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.infrastructure.arq.deps import ARQ_DB_ENGINE
from app.infrastructure.arq.job_runtime import ArqJobRuntime
from app.infrastructure.sqlmodel.job.job_dispatcher import new_job_dispatcher
from app.usecase.job.ports import JobRuntime


async def dispatch_once(
    engine: AsyncEngine,
    *,
    runtime: JobRuntime,
    batch_size: int | None = None,
) -> int:
    """Dispatch one batch of pending jobs."""
    async with AsyncSession(engine) as session:
        dispatcher = new_job_dispatcher(
            session=session,
            runtime=runtime,
        )
        try:
            dispatched = await dispatcher.dispatch_pending(
                batch_size=batch_size or settings.JOB_DISPATCH_BATCH_SIZE,
            )
            await session.commit()
            return dispatched
        except Exception:
            await session.rollback()
            raise


async def dispatch_pending_jobs(ctx: dict[str, Any]) -> int:
    """ARQ cron job that dispatches pending durable jobs."""
    runtime = ArqJobRuntime(
        redis=ctx["redis"],
        queue_name=settings.ARQ_QUEUE_NAME,
    )
    return await dispatch_once(
        ctx[ARQ_DB_ENGINE],
        runtime=runtime,
        batch_size=settings.JOB_DISPATCH_BATCH_SIZE,
    )
