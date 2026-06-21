"""Admin user update schema."""

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserUpdate(SQLModel):
    """Admin user update payload."""

    email: EmailStr | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
