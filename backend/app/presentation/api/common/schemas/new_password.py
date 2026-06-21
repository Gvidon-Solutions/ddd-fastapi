"""Password reset request schema."""

from sqlmodel import Field, SQLModel


class NewPassword(SQLModel):
    """Password reset request."""

    token: str
    new_password: str = Field(min_length=8, max_length=128)
