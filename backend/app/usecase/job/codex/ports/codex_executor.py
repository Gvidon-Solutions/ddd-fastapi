"""Define the Codex executor port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class CodexExecLogFile:
    """Represent a diagnostic file produced by Codex exec."""

    filename: str
    content: bytes
    line_count: int

    @property
    def metadata(self) -> dict:
        """Return file metadata."""
        return {"filename": self.filename, "source": "codex"}


class CodexExecFailedError(RuntimeError):
    """Raised when Codex exec finishes unsuccessfully."""


@dataclass(frozen=True)
class CodexExecResult:
    """Represent one Codex exec result."""

    return_code: int
    output: str
    stdout_lines: list[str]
    stderr_lines: list[str]

    @property
    def output_text(self) -> str:
        """Return the final Codex response text."""
        return self.output

    @property
    def stdout_line_count(self) -> int:
        """Return the captured stdout line count."""
        return len(self.stdout_lines)

    @property
    def stderr_line_count(self) -> int:
        """Return the captured stderr line count."""
        return len(self.stderr_lines)

    def diagnostic_files(self) -> tuple[CodexExecLogFile, ...]:
        """Return diagnostic files worth persisting."""
        files: list[CodexExecLogFile] = []
        if self.stdout_lines:
            files.append(
                CodexExecLogFile(
                    filename="codex_stdout.jsonl",
                    content=_lines_to_bytes(self.stdout_lines),
                    line_count=self.stdout_line_count,
                )
            )
        if self.stderr_lines:
            files.append(
                CodexExecLogFile(
                    filename="codex_stderr.log",
                    content=_lines_to_bytes(self.stderr_lines),
                    line_count=self.stderr_line_count,
                )
            )
        return tuple(files)

    def diagnostic_file_count(self) -> int:
        """Return the number of diagnostic files worth persisting."""
        return len(self.diagnostic_files())

    def raise_for_failure(self) -> None:
        """Raise when Codex exec did not finish successfully."""
        if self.return_code == 0:
            return
        raise CodexExecFailedError(self.failure_message())

    def failure_message(self) -> str:
        """Return a human-readable failure message."""
        error_output = "\n".join(self.stderr_lines).strip()
        if error_output:
            return error_output
        return f"Codex CLI exited with code {self.return_code}"

def _lines_to_bytes(lines: list[str]) -> bytes:
    return ("\n".join(lines) + "\n").encode()


class CodexExecutor(ABC):
    """Execute Codex CLI commands."""

    @abstractmethod
    def is_running(self) -> bool:
        """Return whether this executor currently runs Codex exec."""

    @abstractmethod
    async def cancel(self) -> bool:
        """Cancel the currently running Codex exec process."""

    @abstractmethod
    async def codex_exec(
        self,
        *,
        prompt: str | None = None,
        stdin: str | None = None,
        workdir: Path | None = None,
        command: Sequence[str] = (),
        images: Sequence[Path | str] = (),
        model: str | None = None,
        sandbox_mode: str | None = None,
        configs: Sequence[str] = (),
        enable: Sequence[str] = (),
        disable: Sequence[str] = (),
        profile: str | None = None,
        oss: bool = False,
        local_provider: str | None = None,
        add_dirs: Sequence[Path | str] = (),
        ephemeral: bool = False,
        ignore_user_config: bool = False,
        ignore_rules: bool = False,
        output_schema: Path | str | None = None,
        color: Literal["always", "never", "auto"] | None = None,
        json_output: bool = True,
        strict_config: bool = True,
        skip_git_repo_check: bool = True,
        dangerously_bypass_approvals_and_sandbox: bool = False,
        dangerously_bypass_hook_trust: bool = False,
        output_last_message_path: Path | str | None = None,
        extra_options: Sequence[str] = (),
    ) -> CodexExecResult:
        """Run `codex exec` non-interactively."""
