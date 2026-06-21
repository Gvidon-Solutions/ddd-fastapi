"""Public user registration schema."""

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserRegister(SQLModel):
    """Public registration payload."""

    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
