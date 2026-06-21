"""Define exception for user access violations."""


class UserAccessDeniedError(Exception):
    """Raise when the current user cannot perform an operation."""

    message = "The user does not have enough privileges."

    def __str__(self) -> str:
        """Return the default human-readable error message."""
        return UserAccessDeniedError.message
