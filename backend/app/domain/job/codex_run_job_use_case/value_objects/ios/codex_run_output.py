"""Define typed Codex run job output."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodexRunOutput:
    """Represent the immediate output returned by a Codex run job."""

    output_file_id: str | None
    log_files: int
    generated_files: int
