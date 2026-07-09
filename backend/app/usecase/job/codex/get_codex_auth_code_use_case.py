"""Codex auth code polling use case."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.job import JobId, JobNotFoundError, JobRepository
from app.domain.job.codex_auth_job_use_case import (
    CodexAuthCodeAccessDeniedError,
    CodexAuthCodeJobNotFoundError,
    CodexAuthCodeJobTypeError,
    CodexAuthJobV1,
    CodexAuthSessionRepository,
    CodexAuthSessionStatus,
    CodexDeviceAuth,
)
from app.domain.user.value_objects import UserId

CODEX_AUTH_JOB_TYPE = CodexAuthJobV1.type


class GetCodexAuthCodeUseCase(ABC):
    """Return device-auth code data for a readable Codex auth job."""

    @abstractmethod
    async def execute(
        self,
        job_id: JobId,
        current_user_id: UserId,
    ) -> CodexDeviceAuth | None:
        """Return device auth data once it is available."""


class GetCodexAuthCodeUseCaseImpl(GetCodexAuthCodeUseCase):
    """Read Codex auth polling data for the current user."""

    def __init__(
        self,
        jobs: JobRepository,
        auth_sessions: CodexAuthSessionRepository,
    ) -> None:
        """Store use case dependencies."""
        self.jobs = jobs
        self.auth_sessions = auth_sessions

    async def execute(
        self,
        job_id: JobId,
        current_user_id: UserId,
    ) -> CodexDeviceAuth | None:
        """Return device auth data once it is available."""
        try:
            job = await self.jobs.get(job_id)
        except JobNotFoundError:
            raise CodexAuthCodeJobNotFoundError(str(job_id))

        if job.type != CODEX_AUTH_JOB_TYPE:
            raise CodexAuthCodeJobTypeError(str(job_id))
        if job.initiator.external_id != str(current_user_id):
            raise CodexAuthCodeAccessDeniedError(str(job_id))

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
        return None


def new_get_codex_auth_code_use_case(
    jobs: JobRepository,
    auth_sessions: CodexAuthSessionRepository,
) -> GetCodexAuthCodeUseCase:
    """Instantiate the get-Codex-auth-code use case."""
    return GetCodexAuthCodeUseCaseImpl(
        jobs=jobs,
        auth_sessions=auth_sessions,
    )
