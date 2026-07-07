"""Expose Codex auth job domain exceptions."""

from __future__ import annotations

from app.domain.job.codex_auth_job_use_case.exceptions.codex_auth_code_access_denied_error import (
    CodexAuthCodeAccessDeniedError,
)
from app.domain.job.codex_auth_job_use_case.exceptions.codex_auth_code_error import (
    CodexAuthCodeError,
)
from app.domain.job.codex_auth_job_use_case.exceptions.codex_auth_code_job_not_found_error import (
    CodexAuthCodeJobNotFoundError,
)
from app.domain.job.codex_auth_job_use_case.exceptions.codex_auth_code_job_type_error import (
    CodexAuthCodeJobTypeError,
)
from app.domain.job.codex_auth_job_use_case.exceptions.codex_auth_failed_error import (
    CodexAuthFailedError,
)

__all__ = (
    "CodexAuthCodeAccessDeniedError",
    "CodexAuthCodeError",
    "CodexAuthCodeJobNotFoundError",
    "CodexAuthCodeJobTypeError",
    "CodexAuthFailedError",
)
