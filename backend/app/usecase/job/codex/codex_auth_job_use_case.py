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
        job.status = JobStatus.RUNNING
        job.started_at = now
        job.updated_at = now
        await self.job_events.append(
            job.id,
            Event1CodexAuthStarted(
                created_at=now,
                payload=Event1CodexAuthStartedPayload(),
            ),
        )

        try:
            device_auth = await self.codex_authenticator.start_device_auth()
            now = _now()
            if self.auth_sessions is not None:
                await self.auth_sessions.save_pending(
                    job_id=job.id,
                    verification_url=device_auth.verification_url,
                    user_code=device_auth.device_code,
                    expires_at=now + timedelta(minutes=10),
                )
            job.updated_at = now
            await self.jobs.save(job)
            await self.job_events.append(
                job.id,
                Event2UserLoginRequested(
                    created_at=now,
                    payload=Event2UserLoginRequestedPayload(),
                ),
            )

            auth_result = await self.codex_authenticator.await_for_user_login()
            if not auth_result.authenticated:
                raise RuntimeError(_auth_error_message(auth_result))

            result_payload = CodexAuthJobResult(
                authenticated=auth_result.authenticated,
                error_message=auth_result.error_message,
            )
            now = _now()
            job.status = JobStatus.SUCCEEDED
            job.result = result_payload
            job.finished_at = now
            job.updated_at = now
            job.error = None
            if await _mark_succeeded(self.jobs, job, result_payload, now):
                if self.auth_sessions is not None:
                    await self.auth_sessions.mark_authenticated(job.id)
                await self.job_events.append(
                    job.id,
                    Event3CodexAuthSucceeded(
                        created_at=now,
                        payload=Event3CodexAuthSucceededPayload(
                            summary=result_payload,
                        ),
                    ),
                )
            return result_payload
        except asyncio.CancelledError:
            await self.codex_authenticator.cancel()
            now = _now()
            reason = "Job cancelled"
            job.status = JobStatus.CANCELLED
            job.error = JobError(
                code="CancelledError",
                message=reason,
            )
            job.finished_at = now
            job.updated_at = now
            if await _mark_cancelled(self.jobs, job, job.error, now):
                if self.auth_sessions is not None:
                    await self.auth_sessions.mark_cancelled(job.id, reason)
                await self.job_events.append(
                    job.id,
                    Event5CodexAuthCancelled(
                        created_at=now,
                        payload=Event5CodexAuthCancelledPayload(
                            reason=reason,
                        ),
                    ),
                )
            raise
        except Exception as exc:
            now = _now()
            job.status = JobStatus.FAILED
            job.error = JobError(
                code=type(exc).__name__,
                message=str(exc),
            )
            job.finished_at = now
            job.updated_at = now
            if await _mark_failed(self.jobs, job, job.error, now):
                if self.auth_sessions is not None:
                    await self.auth_sessions.mark_failed(job.id, str(exc))
                await self.job_events.append(
                    job.id,
                    Event4CodexAuthFailed(
                        created_at=now,
                        payload=Event4CodexAuthFailedPayload(
                            error=str(exc),
                        ),
                    ),
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
            job.id,
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
            job.id,
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
            job.id,
            error=error,
            finished_at=finished_at,
        )
    except NotImplementedError:
        await jobs.save(job)
        return True
