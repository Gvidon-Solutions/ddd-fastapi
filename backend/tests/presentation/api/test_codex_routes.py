"""Codex route tests."""

from uuid import UUID

import pytest
from fastapi import HTTPException, Response
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.domain.job import Job
from app.domain.job.codex_auth_job_use_case import (
    CodexAuthInputV1,
    CodexDeviceAuth,
)
from app.domain.job.codex_run_job_use_case import CodexRunInputV1
from app.infrastructure.di import (
    get_codex_auth_code_use_case,
    get_create_job_use_case,
)
from app.main import app
from app.presentation.api.codex import CodexRunCreate
from app.presentation.api.codex.routes.codex import (
    get_codex_auth_code_and_url,
    launch_codex_auth,
    launch_codex_run,
)
from app.presentation.api.common.deps import get_current_user
from app.usecase.job import (
    CodexAuthCodeAccessDeniedError,
    CodexAuthCodeJobNotFoundError,
    CodexAuthCodeJobTypeError,
    CreateJobUseCase,
    GetCodexAuthCodeUseCase,
)

pytestmark = pytest.mark.anyio


class FakeCreateJobUseCase(CreateJobUseCase):
    """Capture created typed jobs."""

    def __init__(self) -> None:
        self.jobs: list[Job] = []

    async def execute(self, job: Job) -> None:
        """Record a created job."""
        self.jobs.append(job)


class FakeGetCodexAuthCodeUseCase(GetCodexAuthCodeUseCase):
    """Return fixed auth code polling data."""

    def __init__(
        self,
        result: CodexDeviceAuth | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[UUID, str]] = []

    async def execute(
        self,
        job_id: UUID,
        current_user_id: str,
    ) -> CodexDeviceAuth | None:
        """Return fixed auth code polling data."""
        self.calls.append((job_id, current_user_id))
        if self.error is not None:
            raise self.error
        return self.result


async def test_launch_codex_auth_queues_auth_job(user) -> None:
    create_job = FakeCreateJobUseCase()

    result = await launch_codex_auth(current_user=user, create_job=create_job)

    assert len(create_job.jobs) == 1
    job = create_job.jobs[0]
    assert result.job_id == job.id
    assert job.type == "execute_codex_auth_job_use_case"
    assert job.name == "Codex auth"
    assert job.description == "Authenticate Codex through device login"
    assert job.input == CodexAuthInputV1()
    assert job.initiator.external_id == str(user.id)
    assert job.initiator.display_name == user.email.value


async def test_launch_codex_run_queues_run_job(user) -> None:
    create_job = FakeCreateJobUseCase()

    result = await launch_codex_run(
        current_user=user,
        create_job=create_job,
        body=CodexRunCreate(prompt="Inspect this repo", workdir="/tmp/work"),
    )

    assert len(create_job.jobs) == 1
    job = create_job.jobs[0]
    assert result.job_id == job.id
    assert job.type == "execute_codex_run_job_use_case"
    assert job.name == "Codex run"
    assert job.description == "Run Codex against a workspace"
    assert job.input == CodexRunInputV1(prompt="Inspect this repo", workdir="/tmp/work")
    assert job.initiator.external_id == str(user.id)


async def test_get_codex_auth_code_returns_empty_response_until_ready(user) -> None:
    job_id = UUID("11111111-1111-1111-1111-111111111111")
    use_case = FakeGetCodexAuthCodeUseCase()

    result = await get_codex_auth_code_and_url(
        current_user=user,
        use_case=use_case,
        job_id=job_id,
    )

    assert isinstance(result, Response)
    assert result.status_code == 204
    assert use_case.calls == [(job_id, str(user.id))]


async def test_get_codex_auth_code_returns_code_when_ready(user) -> None:
    job_id = UUID("11111111-1111-1111-1111-111111111111")
    use_case = FakeGetCodexAuthCodeUseCase(
        CodexDeviceAuth(
            verification_url="https://example.com/device",
            device_code="ABCD-EFGH",
        )
    )

    result = await get_codex_auth_code_and_url(
        current_user=user,
        use_case=use_case,
        job_id=job_id,
    )

    assert not isinstance(result, Response)
    assert result.verification_url == "https://example.com/device"
    assert result.device_code == "ABCD-EFGH"


async def test_get_codex_auth_code_maps_missing_job(user) -> None:
    use_case = FakeGetCodexAuthCodeUseCase(
        error=CodexAuthCodeJobNotFoundError(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_codex_auth_code_and_url(
            current_user=user,
            use_case=use_case,
            job_id=UUID("11111111-1111-1111-1111-111111111111"),
        )

    assert exc_info.value.status_code == 404


async def test_get_codex_auth_code_maps_non_auth_job(user) -> None:
    use_case = FakeGetCodexAuthCodeUseCase(
        error=CodexAuthCodeJobTypeError(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_codex_auth_code_and_url(
            current_user=user,
            use_case=use_case,
            job_id=UUID("11111111-1111-1111-1111-111111111111"),
        )

    assert exc_info.value.status_code == 400


async def test_get_codex_auth_code_maps_access_denied(user) -> None:
    use_case = FakeGetCodexAuthCodeUseCase(
        error=CodexAuthCodeAccessDeniedError(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_codex_auth_code_and_url(
            current_user=user,
            use_case=use_case,
            job_id=UUID("11111111-1111-1111-1111-111111111111"),
        )

    assert exc_info.value.status_code == 403


async def test_codex_auth_api_route_queues_auth_job(user) -> None:
    create_job = FakeCreateJobUseCase()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_create_job_use_case] = lambda: create_job
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"{settings.API_V1_STR}/codex/auth")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"job_id": str(create_job.jobs[0].id)}
    assert create_job.jobs[0].type == "execute_codex_auth_job_use_case"


async def test_codex_run_api_route_queues_run_job(user) -> None:
    create_job = FakeCreateJobUseCase()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_create_job_use_case] = lambda: create_job
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"{settings.API_V1_STR}/codex/run",
                json={"prompt": "Inspect this repo", "workdir": "/tmp/work"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"job_id": str(create_job.jobs[0].id)}
    assert create_job.jobs[0].type == "execute_codex_run_job_use_case"
    assert create_job.jobs[0].input == CodexRunInputV1(
        prompt="Inspect this repo",
        workdir="/tmp/work",
    )


async def test_codex_auth_code_api_route_returns_code(user) -> None:
    use_case = FakeGetCodexAuthCodeUseCase(
        CodexDeviceAuth(
            verification_url="https://example.com/device",
            device_code="ABCD-EFGH",
        )
    )
    job_id = UUID("11111111-1111-1111-1111-111111111111")

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_codex_auth_code_use_case] = lambda: use_case
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"{settings.API_V1_STR}/codex/auth/get_code_and_url/{job_id}",
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "verification_url": "https://example.com/device",
        "device_code": "ABCD-EFGH",
    }
