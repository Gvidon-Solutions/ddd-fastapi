"""Codex auth job entity."""

from __future__ import annotations

from typing import Literal

from app.domain.job.base import JobContract
from app.domain.job.codex_auth_job_use_case.value_objects.codex_auth_result import (
    CodexAuthResult,
)
from app.domain.job.codex_auth_job_use_case.value_objects.ios import (
    CodexAuthInputV1,
)


class CodexAuthJobV1(JobContract[CodexAuthInputV1, CodexAuthResult]):
    """Codex auth job v1 entity."""

    type: Literal["execute_codex_auth_job_use_case"] = "execute_codex_auth_job_use_case"
    version: Literal["v1"] = "v1"
    input = CodexAuthInputV1
    result = CodexAuthResult
