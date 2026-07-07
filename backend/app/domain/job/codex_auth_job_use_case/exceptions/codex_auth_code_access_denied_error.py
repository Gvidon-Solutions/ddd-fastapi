"""Codex auth code access denied error."""

from __future__ import annotations

from app.domain.job.codex_auth_job_use_case.exceptions.codex_auth_code_error import (
    CodexAuthCodeError,
)


class CodexAuthCodeAccessDeniedError(CodexAuthCodeError):
    """Raised when the current user cannot read the requested auth code."""

    detail = "Codex auth code access denied."
