"""Codex auth job result."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CodexAuthJobResult:
    """Represent a completed Codex auth job result."""

    authenticated: bool
    verification_url: str | None = None
    device_code: str | None = None
    error_message: str | None = None

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]

    def to_dict(self) -> dict:
        """Return the result as a JSON-compatible dict."""
        return asdict(self)
