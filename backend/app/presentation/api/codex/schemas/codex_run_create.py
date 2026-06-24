"""Codex run launch payload schema."""

from sqlmodel import Field, SQLModel


class CodexRunCreate(SQLModel):
    """Payload for launching a Codex run job."""

    prompt: str = Field(min_length=1)
    workdir: str | None = Field(default=None, min_length=1)
