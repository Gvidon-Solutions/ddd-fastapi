"""Use case for polling Codex auth device code data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.job import Job, JobRepository
from app.domain.job.codex_auth_job_use_case import CodexDeviceAuth
from app.usecase.job.codex.ports import CodexAuthSessionStatus, CodexAuthSessionStore

CODEX_AUTH_JOB_TYPE = "codex.auth"


class CodexAuthCodeJobNotFoundError(Exception):
    """Raised when the requested job does not exist."""


class CodexAuthCodeJobTypeError(Exception):
    """Raised when the requested job is not a Codex auth job."""


class CodexAuthCodeAccessDeniedError(Exception):
    """Raised when the current user cannot read the requested job."""


class GetCodexAuthCodeAndUrlUseCase(ABC):
    """Define the application boundary for Codex auth polling."""

    @abstractmethod
    async def execute(
        self,
        job_id: UUID,
        current_user_id: str,
    ) -> CodexDeviceAuth | None:
        """Return device auth data once it is available."""


class GetCodexAuthCodeAndUrlUseCaseImpl(GetCodexAuthCodeAndUrlUseCase):
    """Read Codex auth code data from a persisted auth job."""

    def __init__(
        self,
        jobs: JobRepository,
        auth_sessions: CodexAuthSessionStore | None = None,
    ):
        """Store use case dependencies."""
        self.jobs = jobs
        self.auth_sessions = auth_sessions

    async def execute(
        self,
        job_id: UUID,
        current_user_id: str,
    ) -> CodexDeviceAuth | None:
        """Return device auth data once it is available."""
        try:
            job = await self.jobs.get(job_id)
        except KeyError:
            raise CodexAuthCodeJobNotFoundError(str(job_id))

        if job.type != CODEX_AUTH_JOB_TYPE:
            raise CodexAuthCodeJobTypeError(str(job_id))
        if job.root_initiator.id != current_user_id:
            raise CodexAuthCodeAccessDeniedError(str(job_id))
        if self.auth_sessions is not None:
            session = await self.auth_sessions.get(job_id)
            if (
                session is not None
                and session.status == CodexAuthSessionStatus.PENDING
                and isinstance(session.verification_url, str)
                and isinstance(session.user_code, str)
            ):
                return CodexDeviceAuth(
                    verification_url=session.verification_url,
                    device_code=session.user_code,
                )
        return _auth_code_from_job(job)


def new_get_codex_auth_code_and_url_use_case(
    jobs: JobRepository,
    auth_sessions: CodexAuthSessionStore | None = None,
) -> GetCodexAuthCodeAndUrlUseCase:
    """Instantiate the Codex auth code polling use case."""
    return GetCodexAuthCodeAndUrlUseCaseImpl(
        jobs=jobs,
        auth_sessions=auth_sessions,
    )


def _auth_code_from_job(job: Job) -> CodexDeviceAuth | None:
    """Extract Codex device auth data from a job when it is available."""
    candidates = []
    if job.job_stage is not None and job.job_stage.data is not None:
        candidates.append(job.job_stage.data)
    if job.result_summary is not None:
        candidates.append(job.result_summary)

    for candidate in candidates:
        verification_url = _candidate_value(candidate, "verification_url")
        device_code = _candidate_value(candidate, "device_code")
        if isinstance(verification_url, str) and isinstance(device_code, str):
            return CodexDeviceAuth(
                verification_url=verification_url,
                device_code=device_code,
            )
    return None


def _candidate_value(candidate, key: str):
    if isinstance(candidate, dict):
        return candidate.get(key)
    return getattr(candidate, key, None)
