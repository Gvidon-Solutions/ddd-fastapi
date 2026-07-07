"""Pending job dispatch process tests."""

import pytest

from app.domain.job import ActorType, Initiator, JobError, JobId, JobStatus
from app.domain.job.codex_run_job_use_case import CodexRunInputV1, CodexRunJobV1
from app.infrastructure.arq.deps import ARQ_DB_ENGINE
from app.infrastructure.arq.job_dispatcher import dispatch_once, dispatch_pending_jobs
from app.infrastructure.arq.worker import WorkerSettings
from app.infrastructure.sqlmodel.job import JobDTO, new_job_repository
from app.usecase.job import JobRuntime, new_create_job_use_case

pytestmark = pytest.mark.anyio


class FakeJobRuntime(JobRuntime):
    """Record dispatched jobs."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.enqueued: list[tuple[str, JobId]] = []

    async def enqueue(self, job_type: str, job_id: JobId) -> None:
        """Record an enqueued job."""
        if self.fail:
            raise RuntimeError("Redis unavailable")
        self.enqueued.append((job_type, job_id))

    async def cancel(self, job_id: JobId) -> bool:
        """Cancellation is not used by these tests."""
        _ = job_id
        return False

    async def request_cancel(self, job_id: JobId) -> None:
        """Cancellation is not used by these tests."""
        _ = job_id

    async def is_cancel_requested(self, job_id: JobId) -> bool:
        """Cancellation is not used by these tests."""
        _ = job_id
        return False

    async def clear_cancel_request(self, job_id: JobId) -> None:
        """Cancellation is not used by these tests."""
        _ = job_id

    async def await_terminal(
        self,
        job_id: JobId,
        *,
        timeout_seconds: float | None = None,
        poll_delay_seconds: float = 0.5,
    ) -> object:
        """Awaiting is not used by these tests."""
        _ = (job_id, timeout_seconds, poll_delay_seconds)
        return None


class FakeArqRedis:
    """Record ARQ enqueue calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, str]] = []

    async def enqueue_job(
        self,
        job_type: str,
        job_id: str,
        _queue_name: str,
        _job_id: str,
    ) -> object:
        """Record an enqueue call."""
        self.calls.append((job_type, job_id, _queue_name, _job_id))
        return object()


async def test_dispatch_once_enqueues_pending_job(db_session) -> None:
    jobs = new_job_repository(db_session)
    create_job = new_create_job_use_case(jobs=jobs)
    runtime = FakeJobRuntime()
    job = CodexRunJobV1.new(
        initiator=Initiator(type=ActorType.USER, external_id="anton"),
        input=CodexRunInputV1(prompt="Review repository"),
    )

    await create_job.execute(job)
    await db_session.commit()

    dispatched = await dispatch_once(
        db_session.bind,
        runtime=runtime,
        batch_size=10,
    )

    job_row = await db_session.get(JobDTO, job.id.value)
    assert dispatched == 1
    assert runtime.enqueued == [("execute_codex_run_job_use_case", job.id)]
    assert job_row is not None
    assert job_row.status == JobStatus.QUEUED.value
    assert job_row.dispatched_at is not None
    assert job_row.last_dispatch_error is None


async def test_arq_cron_dispatches_pending_jobs_from_worker_context(db_session) -> None:
    jobs = new_job_repository(db_session)
    create_job = new_create_job_use_case(jobs=jobs)
    redis = FakeArqRedis()
    job = CodexRunJobV1.new(
        initiator=Initiator(type=ActorType.USER, external_id="anton"),
        input=CodexRunInputV1(prompt="Review repository"),
    )

    await create_job.execute(job)
    await db_session.commit()

    dispatched = await dispatch_pending_jobs(
        {
            ARQ_DB_ENGINE: db_session.bind,
            "redis": redis,
        }
    )

    assert dispatched == 1
    assert redis.calls == [
        (
            "execute_codex_run_job_use_case",
            str(job.id),
            "agentops-backend-kit-tasks",
            str(job.id),
        )
    ]


async def test_dispatch_once_ignores_non_pending_job(db_session) -> None:
    jobs = new_job_repository(db_session)
    create_job = new_create_job_use_case(jobs=jobs)
    runtime = FakeJobRuntime()
    job = CodexRunJobV1.new(
        initiator=Initiator(type=ActorType.USER, external_id="anton"),
        input=CodexRunInputV1(prompt="Review repository"),
    )

    await create_job.execute(job)
    await jobs.try_mark_cancelled(
        job.id,
        error=JobError(code="cancelled", message="Cancelled"),
        finished_at=job.requested_at,
    )
    await db_session.commit()

    dispatched = await dispatch_once(
        db_session.bind,
        runtime=runtime,
        batch_size=10,
    )

    job_row = await db_session.get(JobDTO, job.id.value)
    assert dispatched == 0
    assert runtime.enqueued == []
    assert job_row is not None
    assert job_row.status == JobStatus.CANCELLED.value


async def test_dispatch_once_keeps_pending_job_when_enqueue_fails(db_session) -> None:
    jobs = new_job_repository(db_session)
    create_job = new_create_job_use_case(jobs=jobs)
    runtime = FakeJobRuntime(fail=True)
    job = CodexRunJobV1.new(
        initiator=Initiator(type=ActorType.USER, external_id="anton"),
        input=CodexRunInputV1(prompt="Review repository"),
    )

    await create_job.execute(job)
    await db_session.commit()

    dispatched = await dispatch_once(
        db_session.bind,
        runtime=runtime,
        batch_size=10,
    )

    job_row = await db_session.get(JobDTO, job.id.value)
    assert dispatched == 0
    assert runtime.enqueued == []
    assert job_row is not None
    assert job_row.status == JobStatus.PENDING.value
    assert job_row.dispatch_attempts == 1
    assert job_row.last_dispatch_error == "Redis unavailable"
    assert job_row.next_dispatch_at is not None
    assert job_row.dispatched_at is None
    assert job_row.started_at is None


def test_worker_settings_registers_job_dispatcher_cron() -> None:
    assert any(
        cron_job.coroutine is dispatch_pending_jobs
        for cron_job in WorkerSettings.cron_jobs
    )
