"""Codex auth application use case."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

from app.domain.job import JobRepository
from app.domain.job.codex_auth_job_use_case import (
    CodexAuthFailedError,
    CodexAuthJobV1,
    CodexAuthResult,
    CodexAuthSessionRepository,
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
from app.usecase.job.codex.ports import (
    CodexAuthenticator,
)

CODEX_AUTH_JOB_TYPE = CodexAuthJobV1.type


class CodexAuthUseCase(ABC):
    """Define the application boundary for Codex device auth."""

    @abstractmethod
    async def execute(self, job: CodexAuthJobV1) -> CodexAuthResult:
        """Execute Codex device auth for one persisted job."""


class CodexAuthUseCaseImpl(CodexAuthUseCase):
    """Execute Codex device auth against a persisted job."""

    def __init__(
        self,
        jobs: JobRepository,
        codex_authenticator: CodexAuthenticator,
        auth_sessions: CodexAuthSessionRepository,
    ):
        """Store use case dependencies."""
        self.jobs = jobs
        self.codex_authenticator = codex_authenticator
        self.auth_sessions = auth_sessions

    async def execute(self, job: CodexAuthJobV1) -> CodexAuthResult:
        """Execute Codex device auth for one persisted job."""
        now = _now()
        await self.jobs.append_event(
            job.id,
            Event1CodexAuthStarted(
                created_at=now,
                payload=Event1CodexAuthStartedPayload(job_id=job.id),
            ),
        )

        try:
            device_auth = await self.codex_authenticator.start_device_auth()
            now = _now()
            await self.auth_sessions.save_pending(
                job_id=job.id,
                verification_url=device_auth.verification_url,
                user_code=device_auth.device_code,
                expires_at=now + timedelta(minutes=10),
            )
            await self.jobs.append_event(
                job.id,
                Event2UserLoginRequested(
                    created_at=now,
                    payload=Event2UserLoginRequestedPayload(job_id=job.id),
                ),
            )

            auth_result = await self.codex_authenticator.await_for_user_login()
            if not auth_result.authenticated:
                raise CodexAuthFailedError(auth_result.error_message)

            result_payload = CodexAuthResult(
                authenticated=auth_result.authenticated,
                error_message=auth_result.error_message,
            )
            now = _now()
            await self.auth_sessions.mark_authenticated(job.id)
            await self.jobs.append_event(
                job.id,
                Event3CodexAuthSucceeded(
                    created_at=now,
                    payload=Event3CodexAuthSucceededPayload(
                        job_id=job.id,
                        summary=result_payload,
                    ),
                ),
            )
            return result_payload
        except asyncio.CancelledError:
            await self.codex_authenticator.cancel()
            now = _now()
            reason = "Job cancelled"
            await self.auth_sessions.mark_cancelled(job.id, reason)
            await self.jobs.append_event(
                job.id,
                Event5CodexAuthCancelled(
                    created_at=now,
                    payload=Event5CodexAuthCancelledPayload(
                        job_id=job.id,
                        reason=reason,
                    ),
                ),
            )
            raise
        except Exception as exc:
            now = _now()
            await self.auth_sessions.mark_failed(job.id, str(exc))
            await self.jobs.append_event(
                job.id,
                Event4CodexAuthFailed(
                    created_at=now,
                    payload=Event4CodexAuthFailedPayload(
                        job_id=job.id,
                        error=str(exc),
                    ),
                ),
            )
            raise

def new_codex_auth_use_case(
    jobs: JobRepository,
    codex_authenticator: CodexAuthenticator,
    auth_sessions: CodexAuthSessionRepository,
) -> CodexAuthUseCase:
    """Instantiate the Codex auth use case."""
    return CodexAuthUseCaseImpl(
        jobs=jobs,
        codex_authenticator=codex_authenticator,
        auth_sessions=auth_sessions,
    )


def _now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)
