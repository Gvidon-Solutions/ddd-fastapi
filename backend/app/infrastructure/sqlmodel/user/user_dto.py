"""User SQLModel DTO."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import EmailStr
from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.domain.user.entities import User
from app.domain.user.value_objects import EmailAddress, FullName, PasswordHash, UserId
from app.infrastructure.sqlmodel.datetime import get_datetime_utc

if TYPE_CHECKING:
    from app.infrastructure.sqlmodel.item.item_dto import ItemDTO


class UserDTO(SQLModel, table=True):
    """Persisted user record."""

    __tablename__ = "user"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    items: list["ItemDTO"] = Relationship(
        back_populates="owner",
        cascade_delete=True,
    )

    def to_entity(self) -> User:
        """Convert this persistence DTO to a domain entity."""
        return User(
            id=UserId(self.id),
            email=EmailAddress(str(self.email)),
            hashed_password=PasswordHash(self.hashed_password),
            full_name=FullName(self.full_name) if self.full_name else None,
            is_active=self.is_active,
            is_superuser=self.is_superuser,
            created_at=self.created_at or get_datetime_utc(),
        )

    @classmethod
    def from_entity(cls, user: User) -> "UserDTO":
        """Build a persistence DTO from a domain entity."""
        return cls(
            id=user.id,
            email=user.email.value,
            hashed_password=user.hashed_password.value,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            full_name=user.full_name.value if user.full_name else None,
            created_at=user.created_at,
        )
