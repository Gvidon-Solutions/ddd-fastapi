"""Define exception for incorrect current passwords."""


class IncorrectPasswordError(Exception):
    """Raise when the current password is incorrect."""

    message = "Incorrect password."

    def __str__(self) -> str:
        """Return the default human-readable error message."""
        return IncorrectPasswordError.message
