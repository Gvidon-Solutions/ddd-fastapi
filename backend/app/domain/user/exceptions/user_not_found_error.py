"""Define exception for missing user entities."""


class UserNotFoundError(Exception):
    """Raise when a requested user cannot be located."""

    message = "The user does not exist."

    def __str__(self) -> str:
        """Return the default human-readable error message."""
        return UserNotFoundError.message
