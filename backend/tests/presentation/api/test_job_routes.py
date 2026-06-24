"""Job route tests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.domain.job import Actor, ActorType, Job, JobRepository, JobStatus
from app.infrastructure.di import get_cancel_job_use_case, get_job_repository
from app.main import app
from app.presentation.api.common.deps import get_current_user
from app.presentation.api.job.routes.jobs import cancel_job
from app.usecase.job import CancelJobUseCase

pytestmark = pytest.mark.anyio


class FakeJobRepository(JobRepository):
    """Store jobs in memory."""

    def __init__(self, jobs: dict[UUID, Job]) -> None:
        self.jobs = jobs

    async def create(self, job: Job) -> None:
        """Create a job."""
        self.jobs[job.job_id] = job

    async def get(self, job_id: UUID) -> Job:
        """Return a job."""
        if job_id not in self.jobs:
            raise KeyError(str(job_id))
        return self.jobs[job_id]

    async def save(self, job: Job) -> None:
        """Save a job."""
        self.jobs[job.job_id] = job


class FakeCancelJobUseCase(CancelJobUseCase):
    """Capture cancel requests."""

    def __init__(self, cancelled: bool = True) -> None:
        self.cancelled = cancelled
        self.calls: list[UUID] = []

    async def execute(self, job_id: UUID) -> bool:
        """Cancel a job."""
        self.calls.append(job_id)
        return self.cancelled


def _job(job_id: UUID, user_id: str) -> Job:
    now = datetime(2026, 6, 24, tzinfo=UTC)
    return Job(
        job_id=job_id,
        job_type="codex_run",
        job_name="Codex run",
        job_description=None,
        job_input=None,
        job_status=JobStatus.QUEUED,
        job_stage=None,
        result_summary=None,
        root_initiator=Actor(type=ActorType.USER, id=user_id),
        parent_job_id=None,
        requested_at=now,
        updated_at=now,
        started_at=None,
        finished_at=None,
        job_error=None,
    )


async def test_cancel_job_returns_success(user) -> None:
    job_id = uuid4()
    use_case = FakeCancelJobUseCase()

    result = await cancel_job(
        current_user=user,
        use_case=use_case,
        jobs=FakeJobRepository({job_id: _job(job_id, str(user.id))}),
        job_id=job_id,
    )

    assert result.job_id == job_id
    assert result.cancelled is True
    assert use_case.calls == [job_id]


async def test_cancel_job_returns_404_when_job_is_missing(user) -> None:
    use_case = FakeCancelJobUseCase()

    with pytest.raises(HTTPException) as exc_info:
        await cancel_job(
            current_user=user,
            use_case=use_case,
            jobs=FakeJobRepository({}),
            job_id=uuid4(),
        )

    assert exc_info.value.status_code == 404
    assert use_case.calls == []


async def test_cancel_job_returns_403_when_job_is_not_owned(user) -> None:
    job_id = uuid4()
    use_case = FakeCancelJobUseCase()

    with pytest.raises(HTTPException) as exc_info:
        await cancel_job(
            current_user=user,
            use_case=use_case,
            jobs=FakeJobRepository({job_id: _job(job_id, "other-user")}),
            job_id=job_id,
        )

    assert exc_info.value.status_code == 403
    assert use_case.calls == []


async def test_cancel_job_returns_409_when_queue_does_not_cancel(user) -> None:
    job_id = uuid4()
    use_case = FakeCancelJobUseCase(cancelled=False)

    with pytest.raises(HTTPException) as exc_info:
        await cancel_job(
            current_user=user,
            use_case=use_case,
            jobs=FakeJobRepository({job_id: _job(job_id, str(user.id))}),
            job_id=job_id,
        )

    assert exc_info.value.status_code == 409
    assert use_case.calls == [job_id]


async def test_cancel_job_api_route_returns_success(user) -> None:
    job_id = uuid4()
    use_case = FakeCancelJobUseCase()
    jobs = FakeJobRepository({job_id: _job(job_id, str(user.id))})

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_cancel_job_use_case] = lambda: use_case
    app.dependency_overrides[get_job_repository] = lambda: jobs
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"{settings.API_V1_STR}/jobs/{job_id}/cancel",
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"job_id": str(job_id), "cancelled": True}
