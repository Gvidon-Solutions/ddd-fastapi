"""Item update schema."""

from sqlmodel import Field, SQLModel


class ItemUpdate(SQLModel):
    """Item update payload."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
