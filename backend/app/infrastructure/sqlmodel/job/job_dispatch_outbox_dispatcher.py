"""Dispatch pending job outbox rows to ARQ."""

from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import JobError, JobStatus
from app.domain.job.base.entities import JobDispatchOutboxStatus
from app.infrastructure.arq.job_workers import worker_bindings
from app.infrastructure.sqlmodel.job.job_dispatch_outbox_dto import (
    JobDispatchOutboxDTO,
)
from app.infrastructure.sqlmodel.job.job_dto import JobDTO, _error_to_record
from app.usecase.job.ports import JobQueue

importlib.import_module("app.infrastructure.arq.jobs")


class JobDispatchOutboxDispatcher:
    """Claim and dispatch pending job outbox rows."""

    def __init__(
        self,
        session: AsyncSession,
        queue: JobQueue,
    ) -> None:
        """Store dispatcher dependencies."""
        self.session = session
        self.queue = queue

    async def dispatch_pending(self, *, batch_size: int = 100) -> int:
        """Dispatch pending rows whose retry time has arrived."""
        now = datetime.now(UTC)
        rows = (
            await self.session.exec(
                select(JobDispatchOutboxDTO)
                .where(
                    JobDispatchOutboxDTO.status
                    == JobDispatchOutboxStatus.PENDING.value,
                    JobDispatchOutboxDTO.next_attempt_at <= now,
                )
                .order_by(
                    JobDispatchOutboxDTO.next_attempt_at,
                    JobDispatchOutboxDTO.created_at,
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

    async def _dispatch(self, row: JobDispatchOutboxDTO, *, now: datetime) -> bool:
        worker = worker_bindings.get(type=row.type, version=row.version)
        if worker is None:
            await self._mark_binding_missing(row, now=now)
            return False

        try:
            await self.queue.enqueue(job_type=worker.__name__, job_id=row.job_id)
        except Exception as exc:
            self._mark_retry(row, error=str(exc), now=now)
            return False

        row.status = JobDispatchOutboxStatus.DISPATCHED.value
        row.dispatched_at = now
        row.updated_at = now
        self.session.add(row)
        return True

    async def _mark_binding_missing(
        self,
        row: JobDispatchOutboxDTO,
        *,
        now: datetime,
    ) -> None:
        error = JobError(
            code="worker_binding_missing",
            message=f"No worker binding for {row.type} {row.version}",
        )
        await self.session.exec(
            update(JobDTO)
            .where(JobDTO.job_id == row.job_id, JobDTO.status == JobStatus.QUEUED.value)
            .values(
                status=JobStatus.FAILED.value,
                result=None,
                error=_error_to_record(error),
                finished_at=now,
                updated_at=now,
            )
        )
        row.status = JobDispatchOutboxStatus.FAILED.value
        row.last_error = error.message
        row.updated_at = now
        self.session.add(row)

    def _mark_retry(
        self,
        row: JobDispatchOutboxDTO,
        *,
        error: str,
        now: datetime,
    ) -> None:
        row.attempts += 1
        row.last_error = error
        row.next_attempt_at = now + _backoff(row.attempts)
        row.updated_at = now
        self.session.add(row)


def _backoff(attempts: int) -> timedelta:
    seconds = min(300, max(1, 2 ** min(attempts, 8)))
    return timedelta(seconds=seconds)


def new_job_dispatch_outbox_dispatcher(
    session: AsyncSession,
    queue: JobQueue,
) -> JobDispatchOutboxDispatcher:
    """Create a job dispatch outbox dispatcher."""
    return JobDispatchOutboxDispatcher(session=session, queue=queue)
