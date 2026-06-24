"""Codex auth result."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodexAuthResult:
    """Represent Codex auth completion."""

    authenticated: bool
    error_message: str | None = None
