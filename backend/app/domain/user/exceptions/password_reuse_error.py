"""Define exception for password reuse."""


class PasswordReuseError(Exception):
    """Raise when a user tries to reuse the current password."""

    message = "New password cannot be the same as the current one."

    def __str__(self) -> str:
        """Return the default human-readable error message."""
        return PasswordReuseError.message
