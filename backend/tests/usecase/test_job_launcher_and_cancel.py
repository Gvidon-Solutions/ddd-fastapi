"""Job launcher and cancellation use case tests."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.job import ActorType, Initiator, Job, JobRepository, JobStatus
from app.domain.job.codex_run_job_use_case import CodexRunInputV1, CodexRunJobV1
from app.usecase.job import JobQueue, new_cancel_job_use_case, new_job_launcher

pytestmark = pytest.mark.anyio


class FakeJobRepository(JobRepository):
    """Store jobs in memory."""

    def __init__(self) -> None:
        self.created: list[Job] = []
        self.jobs: dict[UUID, Job] = {}

    async def create(self, job: Job) -> None:
        """Create a job."""
        self.created.append(job)
        self.jobs[job.id] = job

    async def get(self, job_id: UUID) -> Job:
        """Return a job."""
        return self.jobs[job_id]

    async def save(self, job: Job) -> None:
        """Save a job."""
        self.jobs[job.id] = job


class FakeJobQueue(JobQueue):
    """Record queued jobs."""

    def __init__(self) -> None:
        self.enqueued: list[tuple[str, UUID]] = []
        self.cancelled: list[UUID] = []
        self.cancel_result = True

    async def enqueue(
        self,
        job_type: str,
        job_id: UUID,
    ) -> None:
        """Record an enqueued job."""
        self.enqueued.append((job_type, job_id))

    async def cancel(self, job_id: UUID) -> bool:
        """Record a cancelled job."""
        self.cancelled.append(job_id)
        return self.cancel_result


def _codex_run_job(parent_job_id: UUID | None = None) -> Job:
    return CodexRunJobV1.new(
        initiator=Initiator(
            type=ActorType.USER,
            external_id="anton",
            display_name="Anton",
        ),
        input=CodexRunInputV1(prompt="Review repository"),
        name="Run Codex",
        description="Run Codex against repository",
        parent_job_id=parent_job_id,
    )


async def test_job_launcher_persists_typed_queued_job() -> None:
    jobs = FakeJobRepository()
    launcher = new_job_launcher(jobs=jobs)
    started_at = datetime.now(UTC)
    job = _codex_run_job()

    job_id = await launcher.launch(job)

    created = await jobs.get(job_id)
    assert created.status == JobStatus.QUEUED
    assert created.type == "codex.run"
    assert created.version == "v1"
    assert created.name == "Run Codex"
    assert created.description == "Run Codex against repository"
    assert created.input == CodexRunInputV1(prompt="Review repository")
    assert created.initiator.external_id == "anton"
    assert created.parent_job_id is None
    assert created.requested_at >= started_at
    assert created.updated_at == created.requested_at
    assert created.requested_at.tzinfo == UTC


async def test_job_launcher_keeps_parent_job_id_for_child_jobs() -> None:
    parent_job_id = UUID("11111111-1111-1111-1111-111111111111")
    jobs = FakeJobRepository()
    launcher = new_job_launcher(jobs=jobs)

    job_id = await launcher.launch(_codex_run_job(parent_job_id=parent_job_id))

    job = await jobs.get(job_id)
    assert job.parent_job_id == parent_job_id


async def test_cancel_job_cancels_queue_and_marks_job_cancelled() -> None:
    jobs = FakeJobRepository()
    queue = FakeJobQueue()
    job = _codex_run_job()
    await jobs.create(job)
    cancel_use_case = new_cancel_job_use_case(jobs=jobs, queue=queue)

    cancelled = await cancel_use_case.execute(job.id)

    assert cancelled is True
    assert queue.cancelled == [job.id]
    assert job.status == JobStatus.CANCELLED
    assert job.finished_at is not None
    assert job.error is not None
    assert job.error.code == "CancelledError"


async def test_cancel_job_returns_false_when_queue_does_not_cancel() -> None:
    jobs = FakeJobRepository()
    queue = FakeJobQueue()
    queue.cancel_result = False
    cancel_use_case = new_cancel_job_use_case(jobs=jobs, queue=queue)
    job_id = UUID("11111111-1111-1111-1111-111111111111")

    cancelled = await cancel_use_case.execute(job_id)

    assert cancelled is False
    assert queue.cancelled == [job_id]
