"""Codex auth application use case."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import UUID

from app.domain.job import (
    JobError,
    JobEventRepository,
    JobRepository,
    JobStatus,
)
from app.domain.job.codex_auth_job_use_case import (
    CodexAuthJobResult,
    CodexAuthResult,
    CodexDeviceAuth,
    Event1CodexAuthStarted,
    Event2WaitingForUserLogin,
    Event2WaitingForUserLoginData,
    Event3CodexAuthSucceeded,
    Event3CodexAuthSucceededData,
    Event4CodexAuthFailed,
    Event4CodexAuthFailedData,
    Stage1StartingCodexDeviceAuth,
    Stage2WaitingForUserLogin,
    Stage2WaitingForUserLoginData,
    Stage3CodexAuthCompleted,
    Stage3CodexAuthCompletedData,
    Stage4CodexAuthFailed,
    Stage4CodexAuthFailedData,
)
from app.usecase.codex.ports import CodexAuthenticator


class CodexAuthUseCase(ABC):
    """Define the application boundary for Codex device auth."""

    @abstractmethod
    async def execute(self, job_id: UUID) -> CodexAuthJobResult:
        """Execute Codex device auth for one persisted job."""


class CodexAuthUseCaseImpl(CodexAuthUseCase):
    """Execute Codex device auth against a persisted job."""

    def __init__(
        self,
        jobs: JobRepository,
        job_events: JobEventRepository,
        codex_authenticator: CodexAuthenticator,
    ):
        """Store use case dependencies."""
        self.jobs = jobs
        self.job_events = job_events
        self.codex_authenticator = codex_authenticator

    async def execute(self, job_id: UUID) -> CodexAuthJobResult:
        """Execute Codex device auth for one persisted job."""
        job = await self.jobs.get(job_id)

        job.status = JobStatus.RUNNING
        job.stage = Stage1StartingCodexDeviceAuth()
        job.started_at = _now()
        await self.jobs.save(job)
        await self.job_events.append(
            Event1CodexAuthStarted(
                job_id=job.id,
                created_at=_now(),
            )
        )

        try:
            device_auth = await self.codex_authenticator.start_device_auth()
            waiting_stage = Stage2WaitingForUserLogin(
                data=Stage2WaitingForUserLoginData(
                    verification_url=device_auth.verification_url,
                    user_code=device_auth.user_code,
                    device_code=device_auth.user_code,
                ),
            )
            job.stage = waiting_stage
            await self.jobs.save(job)
            await self.job_events.append(
                Event2WaitingForUserLogin(
                    job_id=job.id,
                    created_at=_now(),
                    data=Event2WaitingForUserLoginData(
                        verification_url=device_auth.verification_url,
                        user_code=device_auth.user_code,
                        device_code=device_auth.user_code,
                    ),
                )
            )

            auth_result = await self.codex_authenticator.await_for_user_login()
            if not auth_result.authenticated:
                raise RuntimeError(_auth_error_message(auth_result))

            result_summary = CodexAuthJobResult(
                authenticated=auth_result.authenticated,
                verification_url=device_auth.verification_url,
                user_code=device_auth.user_code,
                device_code=device_auth.user_code,
                error_message=auth_result.error_message,
            )
            job.status = JobStatus.SUCCEEDED
            job.stage = Stage3CodexAuthCompleted(
                data=Stage3CodexAuthCompletedData(
                    authenticated=auth_result.authenticated,
                    error_message=auth_result.error_message,
                    verification_url=device_auth.verification_url,
                    user_code=device_auth.user_code,
                    device_code=device_auth.user_code,
                ),
            )
            job.result_summary = result_summary.to_dict()
            job.finished_at = _now()
            job.error = None
            await self.jobs.save(job)
            await self.job_events.append(
                Event3CodexAuthSucceeded(
                    job_id=job.id,
                    created_at=_now(),
                    data=Event3CodexAuthSucceededData(summary=result_summary),
                )
            )
            return result_summary
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = JobError(
                code=type(exc).__name__,
                message=str(exc),
            )
            job.stage = Stage4CodexAuthFailed(
                data=Stage4CodexAuthFailedData(error=str(exc)),
            )
            job.finished_at = _now()
            await self.jobs.save(job)
            await self.job_events.append(
                Event4CodexAuthFailed(
                    job_id=job.id,
                    created_at=_now(),
                    data=Event4CodexAuthFailedData(error=str(exc)),
                )
            )
            raise


def new_codex_auth_use_case(
    jobs: JobRepository,
    job_events: JobEventRepository,
    codex_authenticator: CodexAuthenticator,
) -> CodexAuthUseCase:
    """Instantiate the Codex auth use case."""
    return CodexAuthUseCaseImpl(
        jobs=jobs,
        job_events=job_events,
        codex_authenticator=codex_authenticator,
    )


def _auth_error_message(auth_result: CodexAuthResult) -> str:
    """Return a Codex auth failure message."""
    return auth_result.error_message or "Codex auth failed"


def _now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)
