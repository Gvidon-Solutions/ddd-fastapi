"""Define Codex CLI login status."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CodexLoginStatus:
    """Represent whether Codex CLI is authenticated."""

    authenticated: bool
    raw_output: str
