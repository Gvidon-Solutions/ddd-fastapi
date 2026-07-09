"""Await job terminal status use case tests."""

from datetime import datetime
from uuid import UUID

import pytest

from app.domain.job import (
    ActorType,
    Initiator,
    Job,
    JobAwaitTimeoutError,
    JobDetails,
    JobError,
    JobEvent,
    JobFile,
    JobFileRole,
    JobId,
    JobNotFoundError,
    JobReadAccessDeniedError,
    JobReadNotFoundError,
    JobRepository,
    JobStatus,
    JobSummary,
)
from app.domain.job.codex_run_job_use_case import CodexRunInputV1, CodexRunJobV1
from app.domain.user.value_objects import UserId
from app.usecase.job.await_job_terminal_use_case import (
    AwaitJobTerminalUseCaseImpl,
)

pytestmark = pytest.mark.anyio

OWNER_ID = UserId(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
OTHER_USER_ID = UserId(UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))


class FakeJobRepository(JobRepository):
    """Store jobs in memory and return queued status reads."""

    def __init__(self, job: Job | None = None) -> None:
        self.jobs: dict[JobId, Job] = {}
        self.status_reads: list[JobId] = []
        self.detail_reads: list[JobId] = []
        self.next_statuses: list[JobStatus] = []
        if job is not None:
            self.jobs[job.id] = job

    async def create(self, job: Job) -> None:
        """Create a job."""
        self.jobs[job.id] = job

    async def get(self, job_id: JobId) -> Job:
        """Return a job."""
        if job_id not in self.jobs:
            raise JobNotFoundError(str(job_id))
        return self.jobs[job_id]

    async def get_detail(self, job_id: JobId) -> JobDetails:
        """Return job detail."""
        if job_id not in self.jobs:
            raise JobNotFoundError(str(job_id))
        self.detail_reads.append(job_id)
        return _details(self.jobs[job_id])

    async def get_status(self, job_id: JobId) -> JobStatus:
        """Return queued status reads."""
        if job_id not in self.jobs:
            raise JobNotFoundError(str(job_id))
        self.status_reads.append(job_id)
        job = self.jobs[job_id]
        if self.next_statuses:
            job.status = self.next_statuses.pop(0)
        return job.status

    async def list_by_initiator(self, initiator_external_id: str) -> list[JobSummary]:
        """Return jobs by initiator."""
        return [
            _summary(job)
            for job in self.jobs.values()
            if job.initiator.external_id == initiator_external_id
        ]

    async def list_children(self, parent_job_id: JobId) -> list[JobSummary]:
        """Return direct child jobs."""
        return [
            _summary(job)
            for job in self.jobs.values()
            if job.parent_job_id == parent_job_id
        ]

    async def add_file(self, job_file: JobFile) -> None:
        """Associate is unused by these tests."""
        _ = job_file

    async def list_files(
        self,
        job_id: JobId,
        role: JobFileRole | None = None,
    ) -> list[JobFile]:
        """Return no files."""
        _ = (job_id, role)
        return []

    async def append_event(self, job_id: JobId, event: JobEvent) -> None:
        """Append is unused by these tests."""
        _ = (job_id, event)

    async def list_events(self, job_id: JobId) -> list[JobEvent]:
        """Return no events."""
        _ = job_id
        return []

    async def save(self, job: Job) -> None:
        """Save a job."""
        self.jobs[job.id] = job

    async def try_mark_cancelled(
        self,
        job_id: JobId,
        *,
        error: JobError,
        finished_at: datetime,
    ) -> bool:
        """Cancellation is unused by these tests."""
        _ = (job_id, error, finished_at)
        return False


class FakeClock:
    """Advance time when the use case sleeps."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        """Return fake monotonic time."""
        return self.now

    async def sleep(self, seconds: float) -> None:
        """Record and advance fake sleep."""
        self.sleeps.append(seconds)
        self.now += seconds


async def test_await_job_terminal_returns_immediate_terminal_details() -> None:
    # Arrange
    job = _codex_run_job(status=JobStatus.SUCCEEDED)
    jobs = FakeJobRepository(job)
    clock = FakeClock()
    use_case = AwaitJobTerminalUseCaseImpl(
        jobs,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    # Act
    details = await use_case.execute(job.id, current_user_id=OWNER_ID)

    # Assert
    assert details.status == JobStatus.SUCCEEDED
    assert jobs.status_reads == []
    assert jobs.detail_reads == [job.id]
    assert clock.sleeps == []


async def test_await_job_terminal_polls_status_until_terminal() -> None:
    # Arrange
    job = _codex_run_job(status=JobStatus.PENDING)
    jobs = FakeJobRepository(job)
    jobs.next_statuses = [JobStatus.RUNNING, JobStatus.SUCCEEDED]
    clock = FakeClock()
    use_case = AwaitJobTerminalUseCaseImpl(
        jobs,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    # Act
    details = await use_case.execute(
        job.id,
        current_user_id=OWNER_ID,
        timeout_seconds=5.0,
        initial_poll_delay_seconds=0.1,
        max_poll_delay_seconds=1.0,
    )

    # Assert
    assert details.status == JobStatus.SUCCEEDED
    assert jobs.status_reads == [job.id, job.id]
    assert jobs.detail_reads == [job.id]
    assert clock.sleeps == [0.1, 0.2]


async def test_await_job_terminal_raises_when_timeout_expires() -> None:
    # Arrange
    job = _codex_run_job(status=JobStatus.RUNNING)
    jobs = FakeJobRepository(job)
    clock = FakeClock()
    use_case = AwaitJobTerminalUseCaseImpl(
        jobs,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    # Act & Assert
    with pytest.raises(JobAwaitTimeoutError):
        await use_case.execute(
            job.id,
            current_user_id=OWNER_ID,
            timeout_seconds=0.25,
            initial_poll_delay_seconds=0.1,
            max_poll_delay_seconds=0.1,
        )

    assert clock.sleeps[:2] == [0.1, 0.1]
    assert clock.sleeps[2] == pytest.approx(0.05)


async def test_await_job_terminal_raises_when_job_is_missing() -> None:
    # Arrange
    jobs = FakeJobRepository()
    clock = FakeClock()
    use_case = AwaitJobTerminalUseCaseImpl(
        jobs,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    # Act & Assert
    with pytest.raises(JobReadNotFoundError):
        await use_case.execute(
            JobId(UUID("11111111-1111-1111-1111-111111111111")),
            current_user_id=OWNER_ID,
        )


async def test_await_job_terminal_raises_when_job_is_not_owned() -> None:
    # Arrange
    job = _codex_run_job(status=JobStatus.RUNNING)
    jobs = FakeJobRepository(job)
    clock = FakeClock()
    use_case = AwaitJobTerminalUseCaseImpl(
        jobs,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    # Act & Assert
    with pytest.raises(JobReadAccessDeniedError):
        await use_case.execute(job.id, current_user_id=OTHER_USER_ID)

    assert jobs.status_reads == []
    assert clock.sleeps == []


def _codex_run_job(*, status: JobStatus) -> Job:
    job = CodexRunJobV1.new(
        initiator=Initiator(
            type=ActorType.USER,
            external_id=str(OWNER_ID),
            display_name="Anton",
        ),
        input=CodexRunInputV1(prompt="Review repository"),
        name="Run Codex",
        description="Run Codex against repository",
    )
    job.status = status
    return job


def _details(job: Job) -> JobDetails:
    summary = _summary(job)
    return JobDetails(
        id=summary.id,
        type=summary.type,
        version=summary.version,
        name=summary.name,
        status=summary.status,
        initiator=summary.initiator,
        parent_job_id=summary.parent_job_id,
        requested_at=summary.requested_at,
        updated_at=summary.updated_at,
        started_at=summary.started_at,
        finished_at=summary.finished_at,
        input=job.input,
        result=job.result,
        error=job.error,
        files=(),
        events=(),
    )


def _summary(job: Job) -> JobSummary:
    return JobSummary(
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
