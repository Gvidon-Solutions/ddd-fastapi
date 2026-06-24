"""Use case for polling Codex auth device code data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.job import Job, JobRepository
from app.domain.job.codex_auth_job_use_case import CodexDeviceAuth

CODEX_AUTH_JOB_TYPE = "execute_codex_auth_job_use_case"


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

    def __init__(self, jobs: JobRepository):
        """Store use case dependencies."""
        self.jobs = jobs

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

        if job.job_type != CODEX_AUTH_JOB_TYPE:
            raise CodexAuthCodeJobTypeError(str(job_id))
        if job.root_initiator.id != current_user_id:
            raise CodexAuthCodeAccessDeniedError(str(job_id))
        return _auth_code_from_job(job)


def new_get_codex_auth_code_and_url_use_case(
    jobs: JobRepository,
) -> GetCodexAuthCodeAndUrlUseCase:
    """Instantiate the Codex auth code polling use case."""
    return GetCodexAuthCodeAndUrlUseCaseImpl(jobs=jobs)


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
