"""Codex exec failed error."""

from __future__ import annotations


class CodexExecFailedError(Exception):
    """Raised when Codex exec finishes unsuccessfully."""

    detail = "Codex exec failed."

    def __init__(self, detail: str | None = None) -> None:
        """Create an error with default or custom detail."""
        self.detail = detail or self.detail
        super().__init__(self.detail)
