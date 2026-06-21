"""Item creation schema."""

from sqlmodel import Field, SQLModel


class ItemCreate(SQLModel):
    """Item creation payload."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
