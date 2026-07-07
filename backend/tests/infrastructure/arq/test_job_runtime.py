"""ARQ job queue tests."""

from typing import cast
from uuid import UUID

import pytest
from arq.connections import ArqRedis

from app.domain.job import JobId
from app.infrastructure.arq import ArqJobRuntime

pytestmark = pytest.mark.anyio


class FakeArqRedis:
    """Record ARQ enqueue calls."""

    def __init__(self, queued_job: object | None = object()):
        self.queued_job = queued_job
        self.calls: list[tuple[str, str, str, str]] = []

    async def enqueue_job(
        self,
        job_type: str,
        job_id: str,
        _queue_name: str,
        _job_id: str,
    ) -> object | None:
        """Record an enqueue call."""
        self.calls.append((job_type, job_id, _queue_name, _job_id))
        return self.queued_job


async def test_arq_job_runtime_enqueues_name_and_job_id_only() -> None:
    # Arrange
    redis = FakeArqRedis()
    runtime = ArqJobRuntime(redis=cast(ArqRedis, redis), queue_name="jobs")
    job_id = JobId(UUID("11111111-1111-1111-1111-111111111111"))

    # Act
    await runtime.enqueue(
        job_type="codex_run",
        job_id=job_id,
    )

    # Assert
    assert redis.calls == [("codex_run", str(job_id), "jobs", str(job_id))]


async def test_arq_job_runtime_raises_when_arq_does_not_enqueue() -> None:
    # Arrange
    runtime = ArqJobRuntime(
        redis=cast(ArqRedis, FakeArqRedis(queued_job=None)),
        queue_name="jobs",
    )

    # Act / Assert
    with pytest.raises(RuntimeError, match="Job was not enqueued: codex_run"):
        await runtime.enqueue(
            job_type="codex_run",
            job_id=JobId(UUID("11111111-1111-1111-1111-111111111111")),
        )


async def test_arq_job_runtime_cancels_by_domain_job_id(monkeypatch) -> None:
    # Arrange
    aborted_jobs: list[tuple[str, object, str]] = []

    class FakeArqJob:
        def __init__(self, job_id: str, redis: object, _queue_name: str):
            self.job_id = job_id
            self.redis = redis
            self.queue_name = _queue_name

        async def abort(self) -> bool:
            aborted_jobs.append((self.job_id, self.redis, self.queue_name))
            return True

    redis = FakeArqRedis()
    runtime = ArqJobRuntime(redis=cast(ArqRedis, redis), queue_name="jobs")
    job_id = JobId(UUID("11111111-1111-1111-1111-111111111111"))
    monkeypatch.setattr("app.infrastructure.arq.job_runtime.Job", FakeArqJob)

    # Act
    cancelled = await runtime.cancel(job_id)

    # Assert
    assert cancelled is True
    assert aborted_jobs == [(str(job_id), redis, "jobs")]


async def test_arq_job_runtime_awaits_terminal_result(monkeypatch) -> None:
    # Arrange
    awaited_jobs: list[tuple[str, object, str, float | None, float]] = []

    class FakeArqJob:
        def __init__(self, job_id: str, redis: object, _queue_name: str):
            self.job_id = job_id
            self.redis = redis
            self.queue_name = _queue_name

        async def result(
            self,
            timeout: float | None = None,
            *,
            poll_delay: float = 0.5,
        ) -> object:
            awaited_jobs.append(
                (self.job_id, self.redis, self.queue_name, timeout, poll_delay)
            )
            return {"ok": True}

    redis = FakeArqRedis()
    runtime = ArqJobRuntime(redis=cast(ArqRedis, redis), queue_name="jobs")
    job_id = JobId(UUID("11111111-1111-1111-1111-111111111111"))
    monkeypatch.setattr("app.infrastructure.arq.job_runtime.Job", FakeArqJob)

    # Act
    result = await runtime.await_terminal(
        job_id,
        timeout_seconds=10,
        poll_delay_seconds=0.1,
    )

    # Assert
    assert result == {"ok": True}
    assert awaited_jobs == [(str(job_id), redis, "jobs", 10, 0.1)]
