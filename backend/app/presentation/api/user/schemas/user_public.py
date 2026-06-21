"""User response schema."""

import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.domain.user.entities import User


class UserPublic(SQLModel):
    """User response schema."""

    id: uuid.UUID
    email: EmailStr = Field(max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    created_at: datetime | None = None

    @staticmethod
    def from_entity(user: User) -> "UserPublic":
        """Build an API response from a domain entity."""
        return UserPublic(
            id=user.id.value,
            email=user.email.value,
            full_name=user.full_name.value if user.full_name else None,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
        )
