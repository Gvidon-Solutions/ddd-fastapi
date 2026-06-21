"""Codex login status response schema."""

from pydantic import BaseModel


class CodexLoginStatus(BaseModel):
    """Describe Codex CLI authentication state."""

    authenticated: bool
    raw_output: str
