"""Codex auth job contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from app.domain.job.base import JobContract, job_registry


@dataclass(frozen=True)
class CodexAuthInputV1:
    """Input for a Codex auth job."""


@dataclass(frozen=True, init=False)
class CodexAuthResultV1:
    """Successful result for a Codex auth job."""

    authenticated: bool
    error_message: str | None = None

    def __init__(
        self,
        authenticated: bool,
        error_message: str | None = None,
        verification_url: str | None = None,
        device_code: str | None = None,
    ) -> None:
        """Create the result, ignoring legacy sensitive auth-code fields."""
        object.__setattr__(self, "authenticated", authenticated)
        object.__setattr__(self, "error_message", error_message)

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]

    def to_dict(self) -> dict:
        """Return the result as JSON-compatible data."""
        return asdict(self)


@job_registry.register
class CodexAuthJobV1(JobContract[CodexAuthInputV1, CodexAuthResultV1]):
    """Codex auth job contract v1."""

    type: Literal["codex.auth"] = "codex.auth"
    version: Literal["v1"] = "v1"
    input = CodexAuthInputV1
    result = CodexAuthResultV1


CodexAuthJobResult = CodexAuthResultV1
