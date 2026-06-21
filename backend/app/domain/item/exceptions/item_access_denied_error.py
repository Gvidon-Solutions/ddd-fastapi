"""Define exception for item access violations."""


class ItemAccessDeniedError(Exception):
    """Raise when a user is not allowed to access an item."""

    message = "Not enough permissions to access this item."

    def __str__(self) -> str:
        """Return the default human-readable error message."""
        return ItemAccessDeniedError.message
