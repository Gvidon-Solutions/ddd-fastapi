"""Define the User identifier type."""

from typing import NewType
from uuid import UUID, uuid4

UserId = NewType("UserId", UUID)


def new_user_id() -> UserId:
    """Generate a new identifier for a user entity."""
    return UserId(uuid4())
