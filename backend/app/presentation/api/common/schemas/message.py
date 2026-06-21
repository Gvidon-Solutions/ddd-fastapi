"""Generic message response schema."""

from sqlmodel import SQLModel


class Message(SQLModel):
    """Generic message response."""

    message: str
