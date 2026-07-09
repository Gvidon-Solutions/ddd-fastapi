"""Restart job use case tests."""

from datetime import datetime
from uuid import UUID

import pytest

from app.domain.job import (
    ActorType,
    Initiator,
    Job,
    JobDetails,
    JobError,
    JobEvent,
    JobFile,
    JobFileRole,
    JobId,
    JobNotFoundError,
    JobRepository,
    JobRestartAccessDeniedError,
    JobRestartNotAllowedError,
    JobRestartNotFoundError,
    JobStatus,
    JobSummary,
)
from app.domain.job.codex_run_job_use_case import CodexRunInputV1, CodexRunJobV1
from app.domain.user.value_objects import UserId
from app.usecase.job import new_restart_job_use_case

pytestmark = pytest.mark.anyio

OWNER_ID = UserId(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
OTHER_USER_ID = UserId(UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))


class FakeJobRepository(JobRepository):
    """Store jobs in memory."""

    def __init__(self) -> None:
        self.jobs: dict[JobId, Job] = {}
        self.created: list[Job] = []

    async def create(self, job: Job) -> None:
        """Create a job."""
        self.created.append(job)
        self.jobs[job.id] = job

    async def get(self, job_id: JobId) -> Job:
        """Return a job."""
        if job_id not in self.jobs:
            raise JobNotFoundError(str(job_id))
        return self.jobs[job_id]

    async def get_detail(self, job_id: JobId) -> JobDetails:
        """Return job detail."""
        _ = job_id
        raise NotImplementedError

    async def get_status(self, job_id: JobId) -> JobStatus:
        """Return job status."""
        return (await self.get(job_id)).status

    async def list_by_initiator(self, initiator_external_id: str) -> list[JobSummary]:
        """Return jobs by initiator."""
        return [
            _job_summary(job)
            for job in self.jobs.values()
            if job.initiator.external_id == initiator_external_id
        ]

    async def list_children(self, parent_job_id: JobId) -> list[JobSummary]:
        """Return direct child jobs."""
        return [
            _job_summary(job)
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


async def test_restart_job_creates_pending_child_job_from_terminal_job() -> None:
    # Arrange
    jobs = FakeJobRepository()
    original = _codex_run_job(status=JobStatus.FAILED)
    original.result = {"ignored": True}
    original.error = JobError(code="RuntimeError", message="failed")
    await jobs.create(original)
    jobs.created.clear()
    use_case = new_restart_job_use_case(jobs)

    # Act
    restarted_id = await use_case.execute(original.id, current_user_id=OWNER_ID)

    # Assert
    assert len(jobs.created) == 1
    restarted = jobs.created[0]
    assert restarted_id == restarted.id
    assert restarted.id != original.id
    assert type(restarted) is CodexRunJobV1
    assert restarted.type == original.type
    assert restarted.version == original.version
    assert restarted.input == original.input
    assert restarted.name == original.name
    assert restarted.description == original.description
    assert restarted.initiator == original.initiator
    assert restarted.parent_job_id == original.id
    assert restarted.status == JobStatus.PENDING
    assert restarted.result is None
    assert restarted.error is None


async def test_restart_job_allows_succeeded_jobs() -> None:
    # Arrange
    jobs = FakeJobRepository()
    original = _codex_run_job(status=JobStatus.SUCCEEDED)
    await jobs.create(original)
    jobs.created.clear()
    use_case = new_restart_job_use_case(jobs)

    # Act
    restarted_id = await use_case.execute(original.id, current_user_id=OWNER_ID)

    # Assert
    assert restarted_id == jobs.created[0].id
    assert jobs.created[0].parent_job_id == original.id


async def test_restart_job_raises_when_job_is_missing() -> None:
    # Arrange
    jobs = FakeJobRepository()
    use_case = new_restart_job_use_case(jobs)

    # Act & Assert
    with pytest.raises(JobRestartNotFoundError):
        await use_case.execute(
            JobId(UUID("11111111-1111-1111-1111-111111111111")),
            current_user_id=OWNER_ID,
        )


async def test_restart_job_raises_when_job_is_not_owned() -> None:
    # Arrange
    jobs = FakeJobRepository()
    original = _codex_run_job(status=JobStatus.FAILED)
    await jobs.create(original)
    jobs.created.clear()
    use_case = new_restart_job_use_case(jobs)

    # Act & Assert
    with pytest.raises(JobRestartAccessDeniedError):
        await use_case.execute(original.id, current_user_id=OTHER_USER_ID)

    assert jobs.created == []


async def test_restart_job_raises_when_job_is_not_terminal() -> None:
    # Arrange
    jobs = FakeJobRepository()
    original = _codex_run_job(status=JobStatus.RUNNING)
    await jobs.create(original)
    jobs.created.clear()
    use_case = new_restart_job_use_case(jobs)

    # Act & Assert
    with pytest.raises(JobRestartNotAllowedError):
        await use_case.execute(original.id, current_user_id=OWNER_ID)

    assert jobs.created == []


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


def _job_summary(job: Job) -> JobSummary:
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
