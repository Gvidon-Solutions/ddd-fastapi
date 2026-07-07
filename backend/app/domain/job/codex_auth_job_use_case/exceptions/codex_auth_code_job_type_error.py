"""Codex auth code job type error."""

from __future__ import annotations

from app.domain.job.codex_auth_job_use_case.exceptions.codex_auth_code_error import (
    CodexAuthCodeError,
)


class CodexAuthCodeJobTypeError(CodexAuthCodeError):
    """Raised when the requested job is not a Codex auth job."""

    detail = "Job is not a Codex auth job."
