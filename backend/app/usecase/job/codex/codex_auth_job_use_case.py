"""Codex auth application use case."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
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
    Event1CodexAuthStarted,
    Event1CodexAuthStartedPayload,
    Event2UserLoginRequested,
    Event2UserLoginRequestedPayload,
    Event3CodexAuthSucceeded,
    Event3CodexAuthSucceededPayload,
    Event4CodexAuthFailed,
    Event4CodexAuthFailedPayload,
    Event5CodexAuthCancelled,
    Event5CodexAuthCancelledPayload,
    Stage1StartingCodexDeviceAuth,
    Stage2WaitingForUserLogin,
    Stage2WaitingForUserLoginData,
    Stage3CodexAuthCompleted,
    Stage3CodexAuthCompletedData,
    Stage4CodexAuthFailed,
    Stage4CodexAuthFailedData,
    Stage5CodexAuthCancelled,
    Stage5CodexAuthCancelledData,
)
from app.usecase.job.codex.ports import CodexAuthenticator, CodexAuthSessionStore


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
        auth_sessions: CodexAuthSessionStore | None = None,
    ):
        """Store use case dependencies."""
        self.jobs = jobs
        self.job_events = job_events
        self.codex_authenticator = codex_authenticator
        self.auth_sessions = auth_sessions

    async def execute(self, job_id: UUID) -> CodexAuthJobResult:
        """Execute Codex device auth for one persisted job."""
        job = await self.jobs.get(job_id)

        now = _now()
        job.job_status = JobStatus.RUNNING
        job.job_stage = Stage1StartingCodexDeviceAuth(updated_at=now)
        job.started_at = now
        job.updated_at = now
        await self.jobs.save(job)
        await self.job_events.append(
            Event1CodexAuthStarted(
                created_at=now,
                payload=Event1CodexAuthStartedPayload(
                    job_id_issuer=job.job_id,
                ),
            )
        )

        try:
            device_auth = await self.codex_authenticator.start_device_auth()
            now = _now()
            if self.auth_sessions is not None:
                await self.auth_sessions.save_pending(
                    job_id=job.job_id,
                    verification_url=device_auth.verification_url,
                    user_code=device_auth.device_code,
                    expires_at=now + timedelta(minutes=10),
                )
            waiting_stage = Stage2WaitingForUserLogin(
                updated_at=now,
                data=Stage2WaitingForUserLoginData(
                    verification_url=device_auth.verification_url,
                    device_code=device_auth.device_code,
                ),
            )
            job.job_stage = waiting_stage
            job.updated_at = now
            await self.jobs.save(job)
            await self.job_events.append(
                Event2UserLoginRequested(
                    created_at=now,
                    payload=Event2UserLoginRequestedPayload(
                        job_id_issuer=job.job_id,
                        verification_url=device_auth.verification_url,
                        device_code=device_auth.device_code,
                    ),
                )
            )

            auth_result = await self.codex_authenticator.await_for_user_login()
            if not auth_result.authenticated:
                raise RuntimeError(_auth_error_message(auth_result))

            result_summary = CodexAuthJobResult(
                authenticated=auth_result.authenticated,
                error_message=auth_result.error_message,
            )
            now = _now()
            job.job_status = JobStatus.SUCCEEDED
            job.job_stage = Stage3CodexAuthCompleted(
                updated_at=now,
                data=Stage3CodexAuthCompletedData(
                    authenticated=auth_result.authenticated,
                    error_message=auth_result.error_message,
                    verification_url=device_auth.verification_url,
                    device_code=device_auth.device_code,
                ),
            )
            job.result = result_summary
            job.finished_at = now
            job.updated_at = now
            job.job_error = None
            if await _mark_succeeded(self.jobs, job, result_summary, now):
                if self.auth_sessions is not None:
                    await self.auth_sessions.mark_authenticated(job.job_id)
                await self.job_events.append(
                    Event3CodexAuthSucceeded(
                        created_at=now,
                        payload=Event3CodexAuthSucceededPayload(
                            job_id_issuer=job.job_id,
                            summary=result_summary,
                        ),
                    )
                )
            return result_summary
        except asyncio.CancelledError:
            await self.codex_authenticator.cancel()
            now = _now()
            reason = "Job cancelled"
            job.job_status = JobStatus.CANCELLED
            job.job_error = JobError(
                code="CancelledError",
                message=reason,
            )
            job.job_stage = Stage5CodexAuthCancelled(
                updated_at=now,
                data=Stage5CodexAuthCancelledData(reason=reason),
            )
            job.finished_at = now
            job.updated_at = now
            if await _mark_cancelled(self.jobs, job, job.job_error, now):
                if self.auth_sessions is not None:
                    await self.auth_sessions.mark_cancelled(job.job_id, reason)
                await self.job_events.append(
                    Event5CodexAuthCancelled(
                        created_at=now,
                        payload=Event5CodexAuthCancelledPayload(
                            job_id_issuer=job.job_id,
                            reason=reason,
                        ),
                    )
                )
            raise
        except Exception as exc:
            now = _now()
            job.job_status = JobStatus.FAILED
            job.job_error = JobError(
                code=type(exc).__name__,
                message=str(exc),
            )
            job.job_stage = Stage4CodexAuthFailed(
                updated_at=now,
                data=Stage4CodexAuthFailedData(error=str(exc)),
            )
            job.finished_at = now
            job.updated_at = now
            if await _mark_failed(self.jobs, job, job.job_error, now):
                if self.auth_sessions is not None:
                    await self.auth_sessions.mark_failed(job.job_id, str(exc))
                await self.job_events.append(
                    Event4CodexAuthFailed(
                        created_at=now,
                        payload=Event4CodexAuthFailedPayload(
                            job_id_issuer=job.job_id,
                            error=str(exc),
                        ),
                    )
                )
            raise


def new_codex_auth_use_case(
    jobs: JobRepository,
    job_events: JobEventRepository,
    codex_authenticator: CodexAuthenticator,
    auth_sessions: CodexAuthSessionStore | None = None,
) -> CodexAuthUseCase:
    """Instantiate the Codex auth use case."""
    return CodexAuthUseCaseImpl(
        jobs=jobs,
        job_events=job_events,
        codex_authenticator=codex_authenticator,
        auth_sessions=auth_sessions,
    )


def _auth_error_message(auth_result: CodexAuthResult) -> str:
    """Return a Codex auth failure message."""
    return auth_result.error_message or "Codex auth failed"


def _now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


async def _mark_succeeded(
    jobs: JobRepository,
    job,
    result: CodexAuthJobResult,
    finished_at: datetime,
) -> bool:
    try:
        return await jobs.try_mark_succeeded(
            job.job_id,
            result=result,
            finished_at=finished_at,
        )
    except NotImplementedError:
        await jobs.save(job)
        return True


async def _mark_failed(
    jobs: JobRepository,
    job,
    error: JobError,
    finished_at: datetime,
) -> bool:
    try:
        return await jobs.try_mark_failed(
            job.job_id,
            error=error,
            finished_at=finished_at,
        )
    except NotImplementedError:
        await jobs.save(job)
        return True


async def _mark_cancelled(
    jobs: JobRepository,
    job,
    error: JobError,
    finished_at: datetime,
) -> bool:
    try:
        return await jobs.try_mark_cancelled(
            job.job_id,
            error=error,
            finished_at=finished_at,
        )
    except NotImplementedError:
        await jobs.save(job)
        return True
