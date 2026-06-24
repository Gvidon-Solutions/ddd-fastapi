"""LaunchJob use case tests."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.domain.job import Actor, ActorType, Job, JobRepository, JobStatus
from app.usecase.job import JobQueue, new_cancel_job_use_case, new_launch_job_use_case

pytestmark = pytest.mark.anyio


class FakeJobRepository(JobRepository):
    """Store jobs in memory."""

    def __init__(self) -> None:
        self.created: list[Job] = []
        self.jobs: dict[UUID, Job] = {}

    async def create(self, job: Job) -> None:
        """Create a job."""
        self.created.append(job)
        self.jobs[job.job_id] = job

    async def get(self, job_id: UUID) -> Job:
        """Return a job."""
        return self.jobs[job_id]

    async def save(self, job: Job) -> None:
        """Save a job."""
        self.jobs[job.job_id] = job


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


async def test_launch_job_creates_queued_job_and_enqueues_it() -> None:
    # Arrange
    jobs = FakeJobRepository()
    queue = FakeJobQueue()
    use_case = new_launch_job_use_case(
        jobs=jobs,
        queue=queue,
    )
    initiator = Actor(
        type=ActorType.USER,
        id="anton",
        display_name="Anton",
    )

    # Act
    started_at = datetime.now(UTC) - timedelta(seconds=1)
    job_id = await use_case.execute(
        job_type="codex_run",
        job_name="Run Codex",
        root_initiator=initiator,
        job_description="Run Codex against repository",
        job_input={"prompt": "Review repository"},
    )
    finished_at = datetime.now(UTC) + timedelta(seconds=1)

    # Assert
    job = await jobs.get(job_id)
    assert job.job_status == JobStatus.QUEUED
    assert job.job_type == "codex_run"
    assert job.job_name == "Run Codex"
    assert job.job_description == "Run Codex against repository"
    assert job.job_input == {"prompt": "Review repository"}
    assert job.root_initiator == initiator
    assert job.parent_job_id is None
    assert started_at <= job.requested_at <= finished_at
    assert started_at <= job.updated_at <= finished_at
    assert job.updated_at == job.requested_at
    assert job.requested_at.tzinfo == UTC
    assert job.updated_at.tzinfo == UTC
    assert queue.enqueued == [("codex_run", job_id)]


async def test_launch_job_keeps_parent_job_id_for_child_jobs() -> None:
    # Arrange
    parent_job_id = UUID("11111111-1111-1111-1111-111111111111")
    jobs = FakeJobRepository()
    queue = FakeJobQueue()
    use_case = new_launch_job_use_case(
        jobs=jobs,
        queue=queue,
    )

    # Act
    job_id = await use_case.execute(
        job_type="codex_run",
        job_name="Run Codex",
        root_initiator=Actor(type=ActorType.API, id="pipeline"),
        job_input={"prompt": "do child work"},
        parent_job_id=parent_job_id,
    )

    # Assert
    job = await jobs.get(job_id)
    assert job.parent_job_id == parent_job_id


async def test_launch_job_allows_empty_input() -> None:
    # Arrange
    jobs = FakeJobRepository()
    queue = FakeJobQueue()
    use_case = new_launch_job_use_case(
        jobs=jobs,
        queue=queue,
    )

    # Act
    job_id = await use_case.execute(
        job_type="sync_status",
        job_name="Sync status",
        root_initiator=Actor(type=ActorType.SYSTEM),
    )

    # Assert
    job = await jobs.get(job_id)
    assert job.job_input is None
    assert queue.enqueued == [("sync_status", job_id)]


async def test_cancel_job_cancels_queue_and_marks_job_cancelled() -> None:
    # Arrange
    jobs = FakeJobRepository()
    queue = FakeJobQueue()
    launch_use_case = new_launch_job_use_case(jobs=jobs, queue=queue)
    cancel_use_case = new_cancel_job_use_case(jobs=jobs, queue=queue)
    job_id = await launch_use_case.execute(
        job_type="codex_run",
        job_name="Run Codex",
        root_initiator=Actor(type=ActorType.USER, id="anton"),
        job_input={"prompt": "Review repository"},
    )

    # Act
    cancelled = await cancel_use_case.execute(job_id)

    # Assert
    job = await jobs.get(job_id)
    assert cancelled is True
    assert queue.cancelled == [job_id]
    assert job.job_status == JobStatus.CANCELLED
    assert job.finished_at is not None
    assert job.job_error is not None
    assert job.job_error.code == "CancelledError"


async def test_cancel_job_returns_false_when_queue_does_not_cancel() -> None:
    # Arrange
    jobs = FakeJobRepository()
    queue = FakeJobQueue()
    queue.cancel_result = False
    cancel_use_case = new_cancel_job_use_case(jobs=jobs, queue=queue)
    job_id = UUID("11111111-1111-1111-1111-111111111111")

    # Act
    cancelled = await cancel_use_case.execute(job_id)

    # Assert
    assert cancelled is False
    assert queue.cancelled == [job_id]
