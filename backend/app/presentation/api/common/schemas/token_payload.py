"""Decoded JWT token payload schema."""

from sqlmodel import SQLModel


class TokenPayload(SQLModel):
    """Decoded JWT token payload."""

    sub: str | None = None
