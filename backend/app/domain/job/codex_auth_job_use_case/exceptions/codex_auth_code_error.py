"""Base Codex auth code access error."""

from __future__ import annotations


class CodexAuthCodeError(Exception):
    """Base class for Codex auth code access errors."""

    detail = "Codex auth code access error."

    def __init__(self, detail: str | None = None) -> None:
        """Create an error with default or custom detail."""
        self.detail = detail or self.detail
        super().__init__(self.detail)
