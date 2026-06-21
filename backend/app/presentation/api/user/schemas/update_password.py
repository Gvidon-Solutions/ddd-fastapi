"""Current-user password change schema."""

from sqlmodel import Field, SQLModel


class UpdatePassword(SQLModel):
    """Current-user password change payload."""

    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
