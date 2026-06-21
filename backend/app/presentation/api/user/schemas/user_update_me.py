"""Current-user profile update schema."""

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserUpdateMe(SQLModel):
    """Current-user profile update payload."""

    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
