"""Codex route tests."""

from uuid import UUID

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.domain.job import Actor, ActorType
from app.domain.job.codex_auth_job_use_case import CodexDeviceAuth
from app.infrastructure.di import (
    get_codex_auth_code_and_url_use_case,
    get_launch_job_use_case,
)
from app.main import app
from app.presentation.api.codex import CodexRunCreate
from app.presentation.api.codex.routes.codex import (
    CODEX_AUTH_JOB_TYPE,
    CODEX_RUN_JOB_TYPE,
    get_codex_auth_code_and_url,
    launch_codex_auth,
    launch_codex_run,
)
from app.presentation.api.common.deps import get_current_user
from app.usecase.job import (
    CodexAuthCodeAccessDeniedError,
    CodexAuthCodeJobNotFoundError,
    CodexAuthCodeJobTypeError,
    GetCodexAuthCodeAndUrlUseCase,
    LaunchJobUseCase,
)

pytestmark = pytest.mark.anyio


class FakeLaunchJobUseCase(LaunchJobUseCase):
    """Capture launched jobs."""

    def __init__(self) -> None:
        self.job_id = UUID("11111111-1111-1111-1111-111111111111")
        self.calls: list[dict] = []

    async def execute(
        self,
        job_type: str,
        job_name: str,
        root_initiator: Actor,
        job_description: str | None = None,
        job_input: dict | None = None,
        parent_job_id: UUID | None = None,
    ) -> UUID:
        """Record a launched job."""
        self.calls.append(
            {
                "job_type": job_type,
                "job_name": job_name,
                "root_initiator": root_initiator,
                "job_description": job_description,
                "job_input": job_input,
                "parent_job_id": parent_job_id,
            }
        )
        return self.job_id


class FakeGetCodexAuthCodeAndUrlUseCase(GetCodexAuthCodeAndUrlUseCase):
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
    use_case = FakeLaunchJobUseCase()

    result = await launch_codex_auth(current_user=user, use_case=use_case)

    assert result.job_id == use_case.job_id
    assert use_case.calls == [
        {
            "job_type": CODEX_AUTH_JOB_TYPE,
            "job_name": "Codex auth",
            "root_initiator": Actor(
                type=ActorType.USER,
                id=str(user.id),
                display_name=user.email.value,
            ),
            "job_description": "Authenticate Codex through device login",
            "job_input": None,
            "parent_job_id": None,
        }
    ]


async def test_launch_codex_run_queues_run_job(user) -> None:
    use_case = FakeLaunchJobUseCase()

    result = await launch_codex_run(
        current_user=user,
        use_case=use_case,
        body=CodexRunCreate(prompt="Inspect this repo", workdir="/tmp/work"),
    )

    assert result.job_id == use_case.job_id
    assert use_case.calls == [
        {
            "job_type": CODEX_RUN_JOB_TYPE,
            "job_name": "Codex run",
            "root_initiator": Actor(
                type=ActorType.USER,
                id=str(user.id),
                display_name=user.email.value,
            ),
            "job_description": "Run Codex against a workspace",
            "job_input": {"prompt": "Inspect this repo", "workdir": "/tmp/work"},
            "parent_job_id": None,
        }
    ]


async def test_get_codex_auth_code_returns_empty_response_until_ready(user) -> None:
    job_id = UUID("11111111-1111-1111-1111-111111111111")
    use_case = FakeGetCodexAuthCodeAndUrlUseCase()

    result = await get_codex_auth_code_and_url(
        current_user=user,
        use_case=use_case,
        job_id=job_id,
    )

    assert result.status_code == 204
    assert use_case.calls == [(job_id, str(user.id))]


async def test_get_codex_auth_code_returns_code_when_ready(user) -> None:
    job_id = UUID("11111111-1111-1111-1111-111111111111")
    use_case = FakeGetCodexAuthCodeAndUrlUseCase(
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

    assert result.verification_url == "https://example.com/device"
    assert result.device_code == "ABCD-EFGH"


async def test_get_codex_auth_code_maps_missing_job(user) -> None:
    use_case = FakeGetCodexAuthCodeAndUrlUseCase(
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
    use_case = FakeGetCodexAuthCodeAndUrlUseCase(
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
    use_case = FakeGetCodexAuthCodeAndUrlUseCase(
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
    use_case = FakeLaunchJobUseCase()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_launch_job_use_case] = lambda: use_case
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"{settings.API_V1_STR}/codex/auth")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"job_id": str(use_case.job_id)}
    assert use_case.calls[0]["job_type"] == CODEX_AUTH_JOB_TYPE


async def test_codex_run_api_route_queues_run_job(user) -> None:
    use_case = FakeLaunchJobUseCase()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_launch_job_use_case] = lambda: use_case
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
    assert response.json() == {"job_id": str(use_case.job_id)}
    assert use_case.calls[0]["job_type"] == CODEX_RUN_JOB_TYPE
    assert use_case.calls[0]["job_input"] == {
        "prompt": "Inspect this repo",
        "workdir": "/tmp/work",
    }


async def test_codex_auth_code_api_route_returns_code(user) -> None:
    use_case = FakeGetCodexAuthCodeAndUrlUseCase(
        CodexDeviceAuth(
            verification_url="https://example.com/device",
            device_code="ABCD-EFGH",
        )
    )
    job_id = UUID("11111111-1111-1111-1111-111111111111")

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_codex_auth_code_and_url_use_case] = lambda: use_case
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
