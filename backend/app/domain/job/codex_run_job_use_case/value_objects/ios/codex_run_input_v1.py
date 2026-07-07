"""Codex run job input."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodexRunInputV1:
    """Input for a Codex run job."""

    prompt: str
    workdir: str | None = None
