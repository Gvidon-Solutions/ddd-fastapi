"""Job create_job and cancellation use case tests."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.job import (
    ActorType,
    Initiator,
    Job,
    JobCancelAccessDeniedError,
    JobCancelNotAllowedError,
    JobCancelNotFoundError,
    JobCreateNotPendingError,
    JobDetails,
    JobError,
    JobEvent,
    JobFile,
    JobFileRole,
    JobRepository,
    JobStatus,
    JobSummary,
)
from app.domain.job.codex_run_job_use_case import CodexRunInputV1, CodexRunJobV1
from app.usecase.job import (
    JobRuntime,
    new_cancel_job_use_case,
    new_create_job_use_case,
)

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

    async def get_detail(self, job_id: UUID) -> JobDetails:
        """Return job detail."""
        _ = job_id
        raise NotImplementedError

    async def list_by_initiator(self, initiator_external_id: str) -> list[JobSummary]:
        """Return jobs by initiator."""
        return [
            JobSummary(
                id=job.id,
                type=job.type,
                version=job.version,
                name=job.name,
                status=job.status,
                initiator=job.initiator,
                parent_job_id=job.parent_job_id,
                requested_at=job.requested_at,
                updated_at=job.updated_at,
                started_at=job.started_at,
                finished_at=job.finished_at,
            )
            for job in self.jobs.values()
            if job.initiator.external_id == initiator_external_id
        ]

    async def add_file(self, job_file: JobFile) -> None:
        """Associate is unused by these tests."""
        _ = job_file

    async def list_files(
        self,
        job_id: UUID,
        role: JobFileRole | None = None,
    ) -> list[JobFile]:
        """Return no files."""
        _ = (job_id, role)
        return []

    async def append_event(self, job_id: UUID, event: JobEvent) -> None:
        """Append is unused by these tests."""
        _ = (job_id, event)

    async def list_events(self, job_id: UUID) -> list[JobEvent]:
        """Return no events."""
        _ = job_id
        return []

    async def save(self, job: Job) -> None:
        """Save a job."""
        self.jobs[job.id] = job

    async def try_mark_cancelled(
        self,
        job_id: UUID,
        *,
        error: JobError,
        finished_at: datetime,
    ) -> bool:
        """Atomically mark a cancellable job as cancelled."""
        job = self.jobs[job_id]
        if job.status not in {JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING}:
            return False
        job.status = JobStatus.CANCELLED
        job.error = error
        job.finished_at = finished_at
        job.updated_at = finished_at
        return True


class FakeJobRuntime(JobRuntime):
    """Record runtime operations."""

    def __init__(self) -> None:
        self.enqueued: list[tuple[str, UUID]] = []
        self.cancelled: list[UUID] = []
        self.requested: list[UUID] = []
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

    async def request_cancel(self, job_id: UUID) -> None:
        """Record a cancellation request."""
        self.requested.append(job_id)

    async def is_cancel_requested(self, job_id: UUID) -> bool:
        """Return whether cancellation was requested."""
        return job_id in self.requested

    async def clear_cancel_request(self, job_id: UUID) -> None:
        """Clear a cancellation request."""
        if job_id in self.requested:
            self.requested.remove(job_id)

    async def await_terminal(
        self,
        job_id: UUID,
        *,
        timeout_seconds: float | None = None,
        poll_delay_seconds: float = 0.5,
    ) -> object:
        """Awaiting is not used by these tests."""
        _ = (job_id, timeout_seconds, poll_delay_seconds)
        return None


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


async def test_create_job_use_case_persists_typed_pending_job() -> None:
    jobs = FakeJobRepository()
    create_job = new_create_job_use_case(jobs=jobs)
    started_at = datetime.now(UTC)
    job = _codex_run_job()

    await create_job.execute(job)

    created = await jobs.get(job.id)
    assert created.status == JobStatus.PENDING
    assert created.type == "execute_codex_run_job_use_case"
    assert created.version == "v1"
    assert created.name == "Run Codex"
    assert created.description == "Run Codex against repository"
    assert created.input == CodexRunInputV1(prompt="Review repository")
    assert created.initiator.external_id == "anton"
    assert created.parent_job_id is None
    assert created.requested_at >= started_at
    assert created.updated_at == created.requested_at
    assert created.requested_at.tzinfo == UTC


async def test_create_job_use_case_keeps_parent_job_id_for_child_jobs() -> None:
    parent_job_id = UUID("11111111-1111-1111-1111-111111111111")
    jobs = FakeJobRepository()
    create_job = new_create_job_use_case(jobs=jobs)

    child_job = _codex_run_job(parent_job_id=parent_job_id)
    await create_job.execute(child_job)

    job = await jobs.get(child_job.id)
    assert job.parent_job_id == parent_job_id


async def test_create_job_use_case_rejects_non_pending_job() -> None:
    jobs = FakeJobRepository()
    create_job = new_create_job_use_case(jobs=jobs)
    job = _codex_run_job()
    job.status = JobStatus.QUEUED

    with pytest.raises(JobCreateNotPendingError):
        await create_job.execute(job)


async def test_cancel_job_cancels_queue_and_marks_job_cancelled() -> None:
    jobs = FakeJobRepository()
    runtime = FakeJobRuntime()
    job = _codex_run_job()
    job.status = JobStatus.QUEUED
    await jobs.create(job)
    cancel_use_case = new_cancel_job_use_case(jobs=jobs, runtime=runtime)

    await cancel_use_case.execute(job.id, current_user_id="anton")

    assert runtime.cancelled == [job.id]
    assert job.status == JobStatus.CANCELLED
    assert job.finished_at is not None
    assert job.error is not None
    assert job.error.code == "CancelledError"


async def test_cancel_running_job_requests_worker_cancellation_only() -> None:
    jobs = FakeJobRepository()
    runtime = FakeJobRuntime()
    job = _codex_run_job()
    job.status = JobStatus.RUNNING
    await jobs.create(job)
    cancel_use_case = new_cancel_job_use_case(
        jobs=jobs,
        runtime=runtime,
    )

    await cancel_use_case.execute(job.id, current_user_id="anton")

    assert runtime.requested == [job.id]
    assert runtime.cancelled == [job.id]
    assert job.status == JobStatus.RUNNING
    assert job.finished_at is None
    assert job.error is None


async def test_cancel_job_returns_false_when_queue_does_not_cancel() -> None:
    jobs = FakeJobRepository()
    runtime = FakeJobRuntime()
    runtime.cancel_result = False
    cancel_use_case = new_cancel_job_use_case(jobs=jobs, runtime=runtime)
    job = _codex_run_job()
    job.status = JobStatus.QUEUED
    await jobs.create(job)

    with pytest.raises(JobCancelNotAllowedError):
        await cancel_use_case.execute(job.id, current_user_id="anton")

    assert runtime.cancelled == [job.id]


async def test_cancel_job_raises_when_job_is_missing() -> None:
    jobs = FakeJobRepository()
    runtime = FakeJobRuntime()
    cancel_use_case = new_cancel_job_use_case(jobs=jobs, runtime=runtime)

    with pytest.raises(JobCancelNotFoundError):
        await cancel_use_case.execute(
            UUID("11111111-1111-1111-1111-111111111111"),
            current_user_id="anton",
        )

    assert runtime.cancelled == []


async def test_cancel_job_raises_when_job_is_not_owned() -> None:
    jobs = FakeJobRepository()
    runtime = FakeJobRuntime()
    job = _codex_run_job()
    await jobs.create(job)
    cancel_use_case = new_cancel_job_use_case(jobs=jobs, runtime=runtime)

    with pytest.raises(JobCancelAccessDeniedError):
        await cancel_use_case.execute(job.id, current_user_id="other-user")

    assert runtime.cancelled == []
