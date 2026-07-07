"""Expose the Codex auth job use case domain."""

from __future__ import annotations

from app.domain.job.codex_auth_job_use_case.entities import (
    CodexAuthJobV1,
    CodexAuthSession,
)
from app.domain.job.codex_auth_job_use_case.exceptions import (
    CodexAuthCodeAccessDeniedError,
    CodexAuthCodeError,
    CodexAuthCodeJobNotFoundError,
    CodexAuthCodeJobTypeError,
    CodexAuthFailedError,
)
from app.domain.job.codex_auth_job_use_case.repositories import (
    CodexAuthSessionRepository,
)
from app.domain.job.codex_auth_job_use_case.value_objects import (
    CodexAuthInputV1,
    CodexAuthResult,
    CodexAuthSessionStatus,
    CodexDeviceAuth,
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

__all__ = (
    "CodexAuthInputV1",
    "CodexAuthCodeAccessDeniedError",
    "CodexAuthCodeError",
    "CodexAuthCodeJobNotFoundError",
    "CodexAuthCodeJobTypeError",
    "CodexAuthFailedError",
    "CodexAuthJobV1",
    "CodexAuthResult",
    "CodexAuthSession",
    "CodexAuthSessionRepository",
    "CodexAuthSessionStatus",
    "CodexDeviceAuth",
    "Event1CodexAuthStarted",
    "Event1CodexAuthStartedPayload",
    "Event2UserLoginRequested",
    "Event2UserLoginRequestedPayload",
    "Event3CodexAuthSucceeded",
    "Event3CodexAuthSucceededPayload",
    "Event4CodexAuthFailed",
    "Event4CodexAuthFailedPayload",
    "Event5CodexAuthCancelled",
    "Event5CodexAuthCancelledPayload",
)
