"""Codex route tests."""

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import msgspec
import pytest
from fastapi import HTTPException, Response, WebSocket
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.domain.job import (
    ActorType,
    Initiator,
    Job,
    JobDetails,
    JobId,
    JobStatus,
)
from app.domain.job.codex_auth_job_use_case import (
    CodexAuthInputV1,
    CodexDeviceAuth,
)
from app.domain.job.codex_run_job_use_case import CodexRunInputV1
from app.domain.user.value_objects import UserId
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
    listen_codex_job_events,
)
from app.presentation.api.common.deps import get_current_user
from app.usecase.job import (
    CodexAuthCodeAccessDeniedError,
    CodexAuthCodeJobNotFoundError,
    CodexAuthCodeJobTypeError,
    CreateJobUseCase,
    GetCodexAuthCodeUseCase,
    GetJobDetailsUseCase,
    JobEventStream,
    JobEventStreamMessage,
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
        self.calls: list[tuple[JobId, UserId]] = []

    async def execute(
        self,
        job_id: JobId,
        current_user_id: UserId,
    ) -> CodexDeviceAuth | None:
        """Return fixed auth code polling data."""
        self.calls.append((job_id, current_user_id))
        if self.error is not None:
            raise self.error
        return self.result


class FakeGetJobDetailsUseCase(GetJobDetailsUseCase):
    """Return fixed job details."""

    def __init__(self, details: JobDetails) -> None:
        self.details = details
        self.calls: list[tuple[JobId, UserId]] = []

    async def execute(self, job_id: JobId, *, current_user_id: UserId) -> JobDetails:
        """Return fixed job details."""
        self.calls.append((job_id, current_user_id))
        return self.details


class FakeJobEventStream(JobEventStream):
    """Return fixed realtime job event messages."""

    def __init__(self, messages: list[JobEventStreamMessage]) -> None:
        self.messages = messages
        self.calls: list[tuple[JobId, str]] = []

    async def listen(
        self,
        job_id: JobId,
        *,
        last_event_id: str = "0-0",
    ):
        """Yield fixed messages."""
        self.calls.append((job_id, last_event_id))
        for message in self.messages:
            yield message


class FakeWebSocket:
    """Capture WebSocket operations."""

    def __init__(self) -> None:
        self.query_params = {"last_event_id": "0-0"}
        self.accepted = False
        self.text_messages: list[str] = []
        self.closed_code: int | None = None

    async def accept(self) -> None:
        """Accept the fake socket."""
        self.accepted = True

    async def close(self, *, code: int) -> None:
        """Close the fake socket."""
        self.closed_code = code

    async def send_text(self, data: str) -> None:
        """Capture text messages."""
        self.text_messages.append(data)


def _job_details(user, *, job_id: UUID) -> JobDetails:
    now = datetime.now(UTC)
    return JobDetails(
        id=JobId(job_id),
        type="execute_codex_run_job_use_case",
        version="v1",
        name="Codex run",
        status=JobStatus.RUNNING,
        initiator=Initiator(
            type=ActorType.USER,
            external_id=str(user.id),
            display_name=user.email.value,
        ),
        parent_job_id=None,
        requested_at=now,
        updated_at=now,
        started_at=now,
        finished_at=None,
        input={},
        result=None,
        error=None,
        files=(),
        events=(),
    )


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
    assert use_case.calls == [(JobId(job_id), user.id)]


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


async def test_codex_job_events_websocket_streams_typed_codex_events(user) -> None:
    # Arrange
    job_id = UUID("11111111-1111-1111-1111-111111111111")
    details_use_case = FakeGetJobDetailsUseCase(_job_details(user, job_id=job_id))
    event_stream = FakeJobEventStream(
        [
            JobEventStreamMessage(
                stream_id="1-0",
                event={
                    "event_id": "22222222-2222-2222-2222-222222222222",
                    "type": "OtherEventV1",
                    "source": "other",
                    "version": "v1",
                    "created_at": "2026-07-08T12:30:00Z",
                    "payload": {},
                },
            ),
            JobEventStreamMessage(
                stream_id="2-0",
                event={
                    "event_id": "33333333-3333-3333-3333-333333333333",
                    "type": "CodexExecOutputV1",
                    "source": "codex_exec",
                    "version": "v1",
                    "created_at": "2026-07-08T12:31:00Z",
                    "payload": {
                        "job_id": str(job_id),
                        "channel": "stderr",
                        "line_number": 2,
                        "line": "warning",
                    },
                },
            ),
        ]
    )
    websocket = FakeWebSocket()

    # Act
    await listen_codex_job_events(
        websocket=cast(WebSocket, websocket),
        current_user=user,
        job_id=job_id,
        details_use_case=details_use_case,
        event_stream=event_stream,
    )

    # Assert
    assert websocket.accepted is True
    assert websocket.closed_code is None
    assert event_stream.calls == [(JobId(job_id), "0-0")]
    assert len(websocket.text_messages) == 1
    message = msgspec.json.decode(websocket.text_messages[0].encode())
    assert message["stream_id"] == "2-0"
    assert message["event"]["type"] == "CodexExecOutputV1"
    assert message["event"]["payload"]["channel"] == "stderr"
    assert message["event"]["payload"]["line"] == "warning"
