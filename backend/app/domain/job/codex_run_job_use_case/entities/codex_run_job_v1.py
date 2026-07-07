"""Codex run job entity."""

from __future__ import annotations

from typing import Literal

from app.domain.job.base import JobContract
from app.domain.job.codex_run_job_use_case.value_objects.ios import (
    CodexRunInputV1,
    CodexRunOutput,
)


class CodexRunJobV1(JobContract[CodexRunInputV1, CodexRunOutput]):
    """Codex run job v1 entity."""

    type: Literal["execute_codex_run_job_use_case"] = "execute_codex_run_job_use_case"
    version: Literal["v1"] = "v1"
    input = CodexRunInputV1
    result = CodexRunOutput
