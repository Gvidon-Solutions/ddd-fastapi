"""Dispatch pending jobs to ARQ."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, update
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import JobError, JobStatus
from app.infrastructure.arq.job_workers import worker_bindings
from app.infrastructure.sqlmodel.job.job_dto import JobDTO, _error_to_record
from app.usecase.job.ports import JobRuntime


class JobDispatcher:
    """Claim and dispatch pending jobs."""

    def __init__(
        self,
        session: AsyncSession,
        runtime: JobRuntime,
    ) -> None:
        """Store dispatcher dependencies."""
        self.session = session
        self.runtime = runtime

    async def dispatch_pending(self, *, batch_size: int = 100) -> int:
        """Dispatch pending jobs whose retry time has arrived."""
        now = datetime.now(UTC)
        rows = (
            await self.session.exec(
                select(JobDTO)
                .where(
                    col(JobDTO.status) == JobStatus.PENDING.value,
                    or_(
                        col(JobDTO.next_dispatch_at).is_(None),
                        col(JobDTO.next_dispatch_at) <= now,
                    ),
                )
                .order_by(
                    col(JobDTO.next_dispatch_at),
                    col(JobDTO.requested_at),
                )
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
        ).all()

        dispatched = 0
        for row in rows:
            if await self._dispatch(row, now=now):
                dispatched += 1
        return dispatched

    async def _dispatch(self, row: JobDTO, *, now: datetime) -> bool:
        worker = worker_bindings.get(type=row.type, version=row.version)
        if worker is None:
            await self._mark_binding_missing(row, now=now)
            return False

        worker_name = getattr(worker, "__name__", None)
        if not isinstance(worker_name, str):
            await self._mark_binding_missing(row, now=now)
            return False

        try:
            await self.runtime.enqueue(job_type=worker_name, job_id=row.job_id)
        except Exception as exc:
            self._mark_retry(row, error=str(exc), now=now)
            return False

        row.status = JobStatus.QUEUED.value
        row.dispatched_at = now
        row.updated_at = now
        row.last_dispatch_error = None
        self.session.add(row)
        return True

    async def _mark_binding_missing(
        self,
        row: JobDTO,
        *,
        now: datetime,
    ) -> None:
        error = JobError(
            code="worker_binding_missing",
            message=f"No worker binding for {row.type} {row.version}",
        )
        await self.session.exec(
            update(JobDTO)
            .where(
                col(JobDTO.job_id) == row.job_id,
                col(JobDTO.status) == JobStatus.PENDING.value,
            )
            .values(
                status=JobStatus.FAILED.value,
                result=None,
                error=_error_to_record(error),
                finished_at=now,
                updated_at=now,
                last_dispatch_error=error.message,
            )
        )

    def _mark_retry(
        self,
        row: JobDTO,
        *,
        error: str,
        now: datetime,
    ) -> None:
        row.dispatch_attempts += 1
        row.last_dispatch_error = error
        row.next_dispatch_at = now + _backoff(row.dispatch_attempts)
        row.updated_at = now
        self.session.add(row)


def _backoff(attempts: int) -> timedelta:
    seconds = min(300, max(1, 2 ** min(attempts, 8)))
    return timedelta(seconds=seconds)


def new_job_dispatcher(
    session: AsyncSession,
    runtime: JobRuntime,
) -> JobDispatcher:
    """Create a job dispatcher."""
    return JobDispatcher(session=session, runtime=runtime)
