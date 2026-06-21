"""Define exception for invalid login credentials."""


class InvalidCredentialsError(Exception):
    """Raise when login credentials cannot be verified."""

    message = "Incorrect email or password."

    def __str__(self) -> str:
        """Return the default human-readable error message."""
        return InvalidCredentialsError.message
