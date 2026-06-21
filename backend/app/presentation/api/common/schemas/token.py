"""JWT access token response schema."""

from sqlmodel import SQLModel


class Token(SQLModel):
    """JWT access token response."""

    access_token: str
    token_type: str = "bearer"
