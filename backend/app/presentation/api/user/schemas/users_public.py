"""Paginated users response schema."""

from sqlmodel import SQLModel

from app.presentation.api.user.schemas.user_public import UserPublic


class UsersPublic(SQLModel):
    """Paginated users response."""

    data: list[UserPublic]
    count: int
