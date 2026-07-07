"""Job route tests."""

from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.domain.job import (
    JobCancelAccessDeniedError,
    JobCancelNotAllowedError,
    JobCancelNotFoundError,
)
from app.infrastructure.di import get_cancel_job_use_case
from app.main import app
from app.presentation.api.common.deps import get_current_user
from app.presentation.api.job.routes.jobs import cancel_job
from app.usecase.job import CancelJobUseCase

pytestmark = pytest.mark.anyio


class FakeCancelJobUseCase(CancelJobUseCase):
    """Capture cancel requests."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[UUID, str]] = []

    async def execute(self, job_id: UUID, *, current_user_id: str) -> None:
        """Cancel a job."""
        self.calls.append((job_id, current_user_id))
        if self.error is not None:
            raise self.error


async def test_cancel_job_returns_success(user) -> None:
    job_id = uuid4()
    use_case = FakeCancelJobUseCase()

    result = await cancel_job(
        current_user=user,
        use_case=use_case,
        job_id=job_id,
    )

    assert result.job_id == job_id
    assert result.cancelled is True
    assert use_case.calls == [(job_id, str(user.id))]


async def test_cancel_job_returns_404_when_job_is_missing(user) -> None:
    use_case = FakeCancelJobUseCase(error=JobCancelNotFoundError())

    with pytest.raises(HTTPException) as exc_info:
        await cancel_job(
            current_user=user,
            use_case=use_case,
            job_id=uuid4(),
        )

    assert exc_info.value.status_code == 404
    assert len(use_case.calls) == 1


async def test_cancel_job_returns_403_when_job_is_not_owned(user) -> None:
    use_case = FakeCancelJobUseCase(error=JobCancelAccessDeniedError())

    with pytest.raises(HTTPException) as exc_info:
        await cancel_job(
            current_user=user,
            use_case=use_case,
            job_id=uuid4(),
        )

    assert exc_info.value.status_code == 403
    assert len(use_case.calls) == 1


async def test_cancel_job_returns_409_when_queue_does_not_cancel(user) -> None:
    job_id = uuid4()
    use_case = FakeCancelJobUseCase(error=JobCancelNotAllowedError())

    with pytest.raises(HTTPException) as exc_info:
        await cancel_job(
            current_user=user,
            use_case=use_case,
            job_id=job_id,
        )

    assert exc_info.value.status_code == 409
    assert use_case.calls == [(job_id, str(user.id))]


async def test_cancel_job_api_route_returns_success(user) -> None:
    job_id = uuid4()
    use_case = FakeCancelJobUseCase()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_cancel_job_use_case] = lambda: use_case
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
