"""Codex auth code polling use case tests."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.domain.job import ActorType, Initiator, Job, JobRepository, JobStatus
from app.domain.job.codex_auth_job_use_case import CodexAuthInputV1
from app.usecase.job import (
    CODEX_AUTH_JOB_TYPE,
    CodexAuthCodeAccessDeniedError,
    CodexAuthCodeJobNotFoundError,
    CodexAuthCodeJobTypeError,
    CodexAuthSession,
    CodexAuthSessionStatus,
    CodexAuthSessionStore,
    new_get_codex_auth_code_and_url_use_case,
)

pytestmark = pytest.mark.anyio


class FakeJobRepository(JobRepository):
    """Store jobs in memory."""

    def __init__(self, jobs: dict[UUID, Job]) -> None:
        self.jobs = jobs

    async def create(self, job: Job) -> None:
        """Create a job."""
        self.jobs[job.id] = job

    async def get(self, job_id: UUID) -> Job:
        """Return a job."""
        if job_id not in self.jobs:
            raise KeyError(str(job_id))
        return self.jobs[job_id]

    async def save(self, job: Job) -> None:
        """Save a job."""
        self.jobs[job.id] = job


class FakeAuthSessionStore(CodexAuthSessionStore):
    """Store one fake Codex auth session."""

    def __init__(self, session: CodexAuthSession | None = None) -> None:
        self.session = session

    async def save_pending(
        self,
        *,
        job_id: UUID,
        verification_url: str | None,
        user_code: str | None,
        expires_at: datetime,
    ) -> None:
        """Persist pending login data."""
        now = datetime.now(UTC)
        self.session = CodexAuthSession(
            job_id=job_id,
            verification_url=verification_url,
            user_code=user_code,
            expires_at=expires_at,
            status=CodexAuthSessionStatus.PENDING,
            error=None,
            created_at=now,
            updated_at=now,
        )

    async def mark_authenticated(self, job_id: UUID) -> None:
        """Mark authenticated."""

    async def mark_failed(self, job_id: UUID, error: str) -> None:
        """Mark failed."""

    async def mark_cancelled(self, job_id: UUID, reason: str) -> None:
        """Mark cancelled."""

    async def get(self, job_id: UUID) -> CodexAuthSession | None:
        """Return the fake session."""
        if self.session is None or self.session.job_id != job_id:
            return None
        return self.session


def _job(
    *,
    job_id: UUID,
    job_type: str = CODEX_AUTH_JOB_TYPE,
    user_id: str = "user-id",
) -> Job:
    now = datetime(2026, 6, 24, tzinfo=UTC)
    return Job(
        id=job_id,
        type=job_type,
        version="v1",
        name=job_type,
        description=None,
        input=CodexAuthInputV1(),
        result=None,
        status=JobStatus.RUNNING,
        initiator=Initiator(type=ActorType.USER, external_id=user_id),
        parent_job_id=None,
        requested_at=now,
        updated_at=now,
        started_at=now,
        finished_at=None,
        error=None,
    )


def _session(job_id: UUID) -> CodexAuthSession:
    now = datetime(2026, 6, 24, tzinfo=UTC)
    return CodexAuthSession(
        job_id=job_id,
        verification_url="https://example.com/device",
        user_code="ABCD-EFGH",
        expires_at=now + timedelta(minutes=10),
        status=CodexAuthSessionStatus.PENDING,
        error=None,
        created_at=now,
        updated_at=now,
    )


async def test_get_codex_auth_code_returns_none_until_ready() -> None:
    job_id = uuid4()
    use_case = new_get_codex_auth_code_and_url_use_case(
        FakeJobRepository({job_id: _job(job_id=job_id)}),
        auth_sessions=FakeAuthSessionStore(),
    )

    result = await use_case.execute(job_id=job_id, current_user_id="user-id")

    assert result is None


async def test_get_codex_auth_code_returns_session_data_when_ready() -> None:
    job_id = uuid4()
    use_case = new_get_codex_auth_code_and_url_use_case(
        FakeJobRepository({job_id: _job(job_id=job_id)}),
        auth_sessions=FakeAuthSessionStore(_session(job_id)),
    )

    result = await use_case.execute(job_id=job_id, current_user_id="user-id")

    assert result is not None
    assert result.verification_url == "https://example.com/device"
    assert result.device_code == "ABCD-EFGH"


async def test_get_codex_auth_code_raises_when_job_is_missing() -> None:
    use_case = new_get_codex_auth_code_and_url_use_case(FakeJobRepository({}))

    with pytest.raises(CodexAuthCodeJobNotFoundError):
        await use_case.execute(job_id=uuid4(), current_user_id="user-id")


async def test_get_codex_auth_code_raises_when_job_is_not_auth_job() -> None:
    job_id = uuid4()
    use_case = new_get_codex_auth_code_and_url_use_case(
        FakeJobRepository({job_id: _job(job_id=job_id, job_type="codex.run")}),
    )

    with pytest.raises(CodexAuthCodeJobTypeError):
        await use_case.execute(job_id=job_id, current_user_id="user-id")


async def test_get_codex_auth_code_raises_when_user_does_not_own_job() -> None:
    job_id = uuid4()
    use_case = new_get_codex_auth_code_and_url_use_case(
        FakeJobRepository({job_id: _job(job_id=job_id, user_id="other-user")}),
    )

    with pytest.raises(CodexAuthCodeAccessDeniedError):
        await use_case.execute(job_id=job_id, current_user_id="user-id")
