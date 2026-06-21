"""Define exception for inactive users."""


class InactiveUserError(Exception):
    """Raise when an operation requires an active user."""

    message = "The user is inactive."

    def __str__(self) -> str:
        """Return the default human-readable error message."""
        return InactiveUserError.message
