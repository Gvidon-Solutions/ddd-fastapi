"""Codex auth job input."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodexAuthInputV1:
    """Input for a Codex auth job."""
