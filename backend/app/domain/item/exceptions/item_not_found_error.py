"""Define exception for missing item entities."""


class ItemNotFoundError(Exception):
    """Raise when a requested item cannot be located."""

    message = "The item does not exist."

    def __str__(self) -> str:
        """Return the default human-readable error message."""
        return ItemNotFoundError.message
