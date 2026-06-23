"""LaunchJob use case tests."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.job import Actor, ActorType, Job, JobRepository, JobStatus
from app.usecase.job import Clock, JobQueue, new_launch_job_use_case

pytestmark = pytest.mark.anyio


class FixedClock(Clock):
    """Return a fixed test timestamp."""

    def __init__(self, current_time: datetime):
        self.current_time = current_time

    def now(self) -> datetime:
        """Return the fixed timestamp."""
        return self.current_time


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

    async def enqueue(
        self,
        job_name: str,
        job_id: UUID,
    ) -> None:
        """Record an enqueued job."""
        self.enqueued.append((job_name, job_id))


async def test_launch_job_creates_queued_job_and_enqueues_it() -> None:
    # Arrange
    now = datetime(2026, 6, 23, tzinfo=UTC)
    jobs = FakeJobRepository()
    queue = FakeJobQueue()
    use_case = new_launch_job_use_case(
        jobs=jobs,
        queue=queue,
        clock=FixedClock(now),
    )
    initiator = Actor(
        type=ActorType.USER,
        id="anton",
        display_name="Anton",
    )

    # Act
    job_id = await use_case.execute(
        name="run_codex",
        input={"prompt": "Review repository"},
        root_initiator=initiator,
    )

    # Assert
    job = await jobs.get(job_id)
    assert job.status == JobStatus.QUEUED
    assert job.name == "run_codex"
    assert job.input == {"prompt": "Review repository"}
    assert job.root_initiator == initiator
    assert job.parent_job_id is None
    assert job.requested_at == now
    assert queue.enqueued == [("run_codex", job_id)]


async def test_launch_job_keeps_parent_job_id_for_child_jobs() -> None:
    # Arrange
    parent_job_id = UUID("11111111-1111-1111-1111-111111111111")
    jobs = FakeJobRepository()
    queue = FakeJobQueue()
    use_case = new_launch_job_use_case(
        jobs=jobs,
        queue=queue,
        clock=FixedClock(datetime(2026, 6, 23, tzinfo=UTC)),
    )

    # Act
    job_id = await use_case.execute(
        name="run_codex",
        input={"prompt": "do child work"},
        root_initiator=Actor(type=ActorType.API, id="pipeline"),
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
        clock=FixedClock(datetime(2026, 6, 23, tzinfo=UTC)),
    )

    # Act
    job_id = await use_case.execute(
        name="sync_status",
        root_initiator=Actor(type=ActorType.SYSTEM),
    )

    # Assert
    job = await jobs.get(job_id)
    assert job.input is None
    assert queue.enqueued == [("sync_status", job_id)]
