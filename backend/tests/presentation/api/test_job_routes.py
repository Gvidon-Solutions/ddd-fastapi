"""Job route tests."""

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, WebSocket
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.domain.job import (
    Initiator,
    JobCancelAccessDeniedError,
    JobCancelNotAllowedError,
    JobCancelNotFoundError,
    JobDetails,
    JobId,
    JobReadAccessDeniedError,
    JobReadNotFoundError,
    JobStatus,
    JobSummary,
)
from app.domain.user.value_objects import UserId
from app.infrastructure.di import (
    get_cancel_job_use_case,
    get_job_details_use_case,
    get_list_jobs_use_case,
)
from app.main import app
from app.presentation.api.common.deps import get_current_user
from app.presentation.api.job.routes.jobs import (
    cancel_job,
    get_job_details,
    list_jobs,
    listen_job_events,
)
from app.usecase.job import (
    CancelJobUseCase,
    GetJobDetailsUseCase,
    JobEventStream,
    JobEventStreamMessage,
    ListJobsUseCase,
)

pytestmark = pytest.mark.anyio


class FakeCancelJobUseCase(CancelJobUseCase):
    """Capture cancel requests."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[JobId, UserId]] = []

    async def execute(self, job_id: JobId, *, current_user_id: UserId) -> None:
        """Cancel a job."""
        self.calls.append((job_id, current_user_id))
        if self.error is not None:
            raise self.error


class FakeListJobsUseCase(ListJobsUseCase):
    """Return fixed job summaries."""

    def __init__(self, jobs: list[JobSummary]) -> None:
        self.jobs = jobs
        self.calls: list[UserId] = []

    async def execute(self, *, current_user_id: UserId) -> list[JobSummary]:
        """Return fixed job summaries."""
        self.calls.append(current_user_id)
        return self.jobs


class FakeGetJobDetailsUseCase(GetJobDetailsUseCase):
    """Return fixed job details."""

    def __init__(
        self,
        details: JobDetails | None = None,
        error: Exception | None = None,
    ) -> None:
        self.details = details
        self.error = error
        self.calls: list[tuple[JobId, UserId]] = []

    async def execute(self, job_id: JobId, *, current_user_id: UserId) -> JobDetails:
        """Return fixed job details."""
        self.calls.append((job_id, current_user_id))
        if self.error is not None:
            raise self.error
        assert self.details is not None
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

    def __init__(self, *, last_event_id: str = "0-0") -> None:
        self.query_params = {"last_event_id": last_event_id}
        self.accepted = False
        self.closed_code: int | None = None
        self.json_messages: list[dict] = []

    async def accept(self) -> None:
        """Accept the fake socket."""
        self.accepted = True

    async def close(self, *, code: int) -> None:
        """Close the fake socket."""
        self.closed_code = code

    async def send_json(self, data: dict) -> None:
        """Capture JSON messages."""
        self.json_messages.append(data)


def _job_summary(user, *, job_id: UUID | None = None) -> JobSummary:
    now = datetime.now(UTC)
    return JobSummary(
        id=JobId(job_id or uuid4()),
        type="execute_codex_auth_job_use_case",
        version="v1",
        name="Codex auth",
        status=JobStatus.PENDING,
        initiator=Initiator.from_user(user),
        parent_job_id=None,
        requested_at=now,
        updated_at=now,
        started_at=None,
        finished_at=None,
    )


def _job_details(user, *, job_id: UUID | None = None) -> JobDetails:
    summary = _job_summary(user, job_id=job_id)
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
        input={"kind": "test"},
        result=None,
        error=None,
        files=(),
        events=(),
    )


async def test_list_jobs_returns_current_user_jobs(user) -> None:
    # Arrange
    summary = _job_summary(user)
    use_case = FakeListJobsUseCase([summary])

    # Act
    result = await list_jobs(current_user=user, use_case=use_case)

    # Assert
    assert result.count == 1
    assert result.data[0].id == summary.id
    assert result.data[0].status == "pending"
    assert use_case.calls == [user.id]


async def test_get_job_details_returns_current_user_job(user) -> None:
    # Arrange
    job_id = uuid4()
    details = _job_details(user, job_id=job_id)
    use_case = FakeGetJobDetailsUseCase(details=details)

    # Act
    result = await get_job_details(
        current_user=user,
        use_case=use_case,
        job_id=job_id,
    )

    # Assert
    assert result.id == job_id
    assert result.input == {"kind": "test"}
    assert result.events == []
    assert use_case.calls == [(JobId(job_id), user.id)]


async def test_list_job_events_streams_authorized_job_events(user) -> None:
    # Arrange
    job_id = uuid4()
    details = _job_details(user, job_id=job_id)
    details_use_case = FakeGetJobDetailsUseCase(details=details)
    event_stream = FakeJobEventStream(
        [
            JobEventStreamMessage(
                stream_id="1-0",
                event={"type": "CodexRunStartedV1", "payload": {"job_id": str(job_id)}},
            )
        ]
    )
    websocket = FakeWebSocket(last_event_id="0-0")

    # Act
    await listen_job_events(
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
    assert websocket.json_messages == [
        {
            "stream_id": "1-0",
            "event": {"type": "CodexRunStartedV1", "payload": {"job_id": str(job_id)}},
        }
    ]


async def test_get_job_details_returns_404_when_job_is_missing(user) -> None:
    # Arrange
    use_case = FakeGetJobDetailsUseCase(error=JobReadNotFoundError())

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_job_details(
            current_user=user,
            use_case=use_case,
            job_id=uuid4(),
        )

    assert exc_info.value.status_code == 404


async def test_get_job_details_returns_403_when_job_is_not_owned(user) -> None:
    # Arrange
    use_case = FakeGetJobDetailsUseCase(error=JobReadAccessDeniedError())

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_job_details(
            current_user=user,
            use_case=use_case,
            job_id=uuid4(),
        )

    assert exc_info.value.status_code == 403


async def test_list_jobs_api_route_returns_current_user_jobs(user) -> None:
    # Arrange
    summary = _job_summary(user)
    use_case = FakeListJobsUseCase([summary])

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_list_jobs_use_case] = lambda: use_case
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Act
            response = await client.get(f"{settings.API_V1_STR}/jobs/")
    finally:
        app.dependency_overrides.clear()

    # Assert
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["data"][0]["id"] == str(summary.id)


async def test_get_job_details_api_route_returns_current_user_job(user) -> None:
    # Arrange
    job_id = uuid4()
    details = _job_details(user, job_id=job_id)
    use_case = FakeGetJobDetailsUseCase(details=details)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_job_details_use_case] = lambda: use_case
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Act
            response = await client.get(f"{settings.API_V1_STR}/jobs/{job_id}")
    finally:
        app.dependency_overrides.clear()

    # Assert
    assert response.status_code == 200
    assert response.json()["id"] == str(job_id)
    assert response.json()["input"] == {"kind": "test"}


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
    assert use_case.calls == [(JobId(job_id), user.id)]


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
    assert use_case.calls == [(JobId(job_id), user.id)]


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
