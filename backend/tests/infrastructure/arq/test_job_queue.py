"""ARQ job queue tests."""

from uuid import UUID

import pytest

from app.infrastructure.arq import ArqJobQueue

pytestmark = pytest.mark.anyio


class FakeArqRedis:
    """Record ARQ enqueue calls."""

    def __init__(self, queued_job: object | None = object()):
        self.queued_job = queued_job
        self.calls: list[tuple[str, str, str]] = []

    async def enqueue_job(
        self,
        job_name: str,
        job_id: str,
        _queue_name: str,
    ) -> object | None:
        """Record an enqueue call."""
        self.calls.append((job_name, job_id, _queue_name))
        return self.queued_job


async def test_arq_job_queue_enqueues_name_and_job_id_only() -> None:
    # Arrange
    redis = FakeArqRedis()
    queue = ArqJobQueue(redis=redis, queue_name="jobs")
    job_id = UUID("11111111-1111-1111-1111-111111111111")

    # Act
    await queue.enqueue(
        job_name="run_codex",
        job_id=job_id,
    )

    # Assert
    assert redis.calls == [("run_codex", str(job_id), "jobs")]


async def test_arq_job_queue_raises_when_arq_does_not_enqueue() -> None:
    # Arrange
    queue = ArqJobQueue(redis=FakeArqRedis(queued_job=None), queue_name="jobs")

    # Act / Assert
    with pytest.raises(RuntimeError, match="Job was not enqueued: run_codex"):
        await queue.enqueue(
            job_name="run_codex",
            job_id=UUID("11111111-1111-1111-1111-111111111111"),
        )
