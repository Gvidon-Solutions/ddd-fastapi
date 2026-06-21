"""Define exception for duplicate email addresses."""


class EmailAlreadyExistsError(Exception):
    """Raise when a user email is already registered."""

    message = "The user with this email already exists."

    def __str__(self) -> str:
        """Return the default human-readable error message."""
        return EmailAlreadyExistsError.message
