"""Codex auth code job not found error."""

from __future__ import annotations

from app.domain.job.codex_auth_job_use_case.exceptions.codex_auth_code_error import (
    CodexAuthCodeError,
)


class CodexAuthCodeJobNotFoundError(CodexAuthCodeError):
    """Raised when the requested Codex auth job does not exist."""

    detail = "Codex auth job not found."
