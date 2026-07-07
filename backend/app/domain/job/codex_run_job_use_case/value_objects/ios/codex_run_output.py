"""Define typed Codex run job output."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.file import FileId


@dataclass(frozen=True)
class CodexRunOutput:
    """Represent the immediate output returned by a Codex run job."""

    output_file_id: FileId | None
    log_files: int
    generated_files: int
