"""Delete job use case tests."""

from datetime import datetime
from uuid import UUID

import pytest

from app.domain.job import (
    ActorType,
    Initiator,
    Job,
    JobDeleteAccessDeniedError,
    JobDeleteNotAllowedError,
    JobDeleteNotFoundError,
    JobDetails,
    JobError,
    JobEvent,
    JobFile,
    JobFileRole,
    JobHasChildrenError,
    JobId,
    JobNotFoundError,
    JobRepository,
    JobStatus,
    JobSummary,
)
from app.domain.job.codex_run_job_use_case import CodexRunInputV1, CodexRunJobV1
from app.domain.user.value_objects import UserId
from app.usecase.job import new_delete_job_use_case

pytestmark = pytest.mark.anyio

OWNER_ID = UserId(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
OTHER_USER_ID = UserId(UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))
_TERMINAL_STATUSES = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}


class FakeJobRepository(JobRepository):
    """Store jobs in memory."""

    def __init__(self) -> None:
        self.jobs: dict[JobId, Job] = {}
        self.deleted: list[JobId] = []

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

    async def delete(self, job_id: JobId, *, cascade_children: bool = False) -> None:
        """Delete a terminal job."""
        job = await self.get(job_id)
        if job.status not in _TERMINAL_STATUSES:
            raise JobDeleteNotAllowedError(str(job_id))

        children = [
            child for child in self.jobs.values() if child.parent_job_id == job_id
        ]
        if children and not cascade_children:
            raise JobHasChildrenError(str(job_id))
        for child in children:
            await self.delete(child.id, cascade_children=True)

        self.deleted.append(job_id)
        del self.jobs[job_id]


async def test_delete_job_deletes_owned_terminal_job() -> None:
    # Arrange
    jobs = FakeJobRepository()
    job = _codex_run_job(status=JobStatus.SUCCEEDED)
    await jobs.create(job)
    use_case = new_delete_job_use_case(jobs)

    # Act
    await use_case.execute(job.id, current_user_id=OWNER_ID)

    # Assert
    assert job.id not in jobs.jobs
    assert jobs.deleted == [job.id]


async def test_delete_job_raises_when_job_is_missing() -> None:
    # Arrange
    jobs = FakeJobRepository()
    use_case = new_delete_job_use_case(jobs)

    # Act & Assert
    with pytest.raises(JobDeleteNotFoundError):
        await use_case.execute(
            JobId(UUID("11111111-1111-1111-1111-111111111111")),
            current_user_id=OWNER_ID,
        )


async def test_delete_job_raises_when_job_is_not_owned() -> None:
    # Arrange
    jobs = FakeJobRepository()
    job = _codex_run_job(status=JobStatus.SUCCEEDED)
    await jobs.create(job)
    use_case = new_delete_job_use_case(jobs)

    # Act & Assert
    with pytest.raises(JobDeleteAccessDeniedError):
        await use_case.execute(job.id, current_user_id=OTHER_USER_ID)

    assert job.id in jobs.jobs
    assert jobs.deleted == []


async def test_delete_job_raises_when_job_is_not_terminal() -> None:
    # Arrange
    jobs = FakeJobRepository()
    job = _codex_run_job(status=JobStatus.RUNNING)
    await jobs.create(job)
    use_case = new_delete_job_use_case(jobs)

    # Act & Assert
    with pytest.raises(JobDeleteNotAllowedError):
        await use_case.execute(job.id, current_user_id=OWNER_ID)

    assert job.id in jobs.jobs


async def test_delete_job_deletes_owned_terminal_descendants() -> None:
    # Arrange
    jobs = FakeJobRepository()
    parent = _codex_run_job(status=JobStatus.SUCCEEDED)
    child = _codex_run_job(parent_job_id=parent.id, status=JobStatus.FAILED)
    grandchild = _codex_run_job(
        parent_job_id=child.id,
        status=JobStatus.CANCELLED,
    )
    for job in [parent, child, grandchild]:
        await jobs.create(job)
    use_case = new_delete_job_use_case(jobs)

    # Act
    await use_case.execute(parent.id, current_user_id=OWNER_ID)

    # Assert
    assert jobs.jobs == {}
    assert jobs.deleted == [grandchild.id, child.id, parent.id]


async def test_delete_job_rejects_when_descendant_is_not_terminal() -> None:
    # Arrange
    jobs = FakeJobRepository()
    parent = _codex_run_job(status=JobStatus.SUCCEEDED)
    child = _codex_run_job(parent_job_id=parent.id, status=JobStatus.RUNNING)
    await jobs.create(parent)
    await jobs.create(child)
    use_case = new_delete_job_use_case(jobs)

    # Act & Assert
    with pytest.raises(JobDeleteNotAllowedError):
        await use_case.execute(parent.id, current_user_id=OWNER_ID)

    assert parent.id in jobs.jobs
    assert child.id in jobs.jobs
    assert jobs.deleted == []


async def test_delete_job_rejects_when_descendant_is_not_owned() -> None:
    # Arrange
    jobs = FakeJobRepository()
    parent = _codex_run_job(status=JobStatus.SUCCEEDED)
    child = _codex_run_job(
        parent_job_id=parent.id,
        status=JobStatus.SUCCEEDED,
        owner_id=OTHER_USER_ID,
    )
    await jobs.create(parent)
    await jobs.create(child)
    use_case = new_delete_job_use_case(jobs)

    # Act & Assert
    with pytest.raises(JobDeleteAccessDeniedError):
        await use_case.execute(parent.id, current_user_id=OWNER_ID)

    assert parent.id in jobs.jobs
    assert child.id in jobs.jobs
    assert jobs.deleted == []


def _codex_run_job(
    *,
    status: JobStatus,
    parent_job_id: JobId | None = None,
    owner_id: UserId = OWNER_ID,
) -> Job:
    job = CodexRunJobV1.new(
        initiator=Initiator(
            type=ActorType.USER,
            external_id=str(owner_id),
            display_name="Anton",
        ),
        input=CodexRunInputV1(prompt="Review repository"),
        name="Run Codex",
        description="Run Codex against repository",
        parent_job_id=parent_job_id,
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
