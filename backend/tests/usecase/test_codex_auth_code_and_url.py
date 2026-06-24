"""Codex auth code polling use case tests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.domain.job import Actor, ActorType, Job, JobRepository, JobStage, JobStatus
from app.usecase.job import (
    CODEX_AUTH_JOB_TYPE,
    CodexAuthCodeAccessDeniedError,
    CodexAuthCodeJobNotFoundError,
    CodexAuthCodeJobTypeError,
    new_get_codex_auth_code_and_url_use_case,
)

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


def _job(
    *,
    job_id: UUID,
    job_type: str = CODEX_AUTH_JOB_TYPE,
    user_id: str = "user-id",
    job_stage: JobStage | None = None,
    result_summary: dict | None = None,
) -> Job:
    now = datetime(2026, 6, 24, tzinfo=UTC)
    return Job(
        job_id=job_id,
        job_type=job_type,
        job_name=job_type,
        job_description=None,
        job_input=None,
        job_status=JobStatus.RUNNING,
        job_stage=job_stage,
        result_summary=result_summary,
        root_initiator=Actor(type=ActorType.USER, id=user_id),
        parent_job_id=None,
        requested_at=now,
        updated_at=now,
        started_at=now,
        finished_at=None,
        job_error=None,
    )


async def test_get_codex_auth_code_returns_none_until_ready() -> None:
    job_id = uuid4()
    use_case = new_get_codex_auth_code_and_url_use_case(
        FakeJobRepository({job_id: _job(job_id=job_id)}),
    )

    result = await use_case.execute(job_id=job_id, current_user_id="user-id")

    assert result is None


async def test_get_codex_auth_code_returns_stage_data_when_ready() -> None:
    job_id = uuid4()
    use_case = new_get_codex_auth_code_and_url_use_case(
        FakeJobRepository(
            {
                job_id: _job(
                    job_id=job_id,
                    job_stage=JobStage(
                        key="codex_auth",
                        data={
                            "verification_url": "https://example.com/device",
                            "device_code": "ABCD-EFGH",
                        },
                    ),
                )
            }
        ),
    )

    result = await use_case.execute(job_id=job_id, current_user_id="user-id")

    assert result is not None
    assert result.verification_url == "https://example.com/device"
    assert result.device_code == "ABCD-EFGH"


async def test_get_codex_auth_code_returns_result_summary_when_ready() -> None:
    job_id = uuid4()
    use_case = new_get_codex_auth_code_and_url_use_case(
        FakeJobRepository(
            {
                job_id: _job(
                    job_id=job_id,
                    result_summary={
                        "verification_url": "https://example.com/device",
                        "device_code": "ABCD-EFGH",
                    },
                )
            }
        ),
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
        FakeJobRepository({job_id: _job(job_id=job_id, job_type="codex_run")}),
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
