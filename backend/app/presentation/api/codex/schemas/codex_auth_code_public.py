"""Codex auth code polling response schema."""

from sqlmodel import SQLModel


class CodexAuthCodePublic(SQLModel):
    """Verification URL and device code for a Codex auth job."""

    verification_url: str
    device_code: str
