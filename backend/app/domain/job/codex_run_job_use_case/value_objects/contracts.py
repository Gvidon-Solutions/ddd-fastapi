"""Codex run job contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.job.base import JobContract, job_registry


@dataclass(frozen=True)
class CodexRunInputV1:
    """Input for a Codex run job."""

    prompt: str
    workdir: str | None = None


@dataclass(frozen=True)
class CodexRunResultV1:
    """Successful result for a Codex run job."""

    log_files: int
    generated_files: int


@job_registry.register
class CodexRunJobV1(JobContract[CodexRunInputV1, CodexRunResultV1]):
    """Codex run job contract v1."""

    type: Literal["codex.run"] = "codex.run"
    version: Literal["v1"] = "v1"
    input = CodexRunInputV1
    result = CodexRunResultV1
