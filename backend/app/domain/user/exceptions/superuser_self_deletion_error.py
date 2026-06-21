"""Define exception for deleting a superuser's own account."""


class SuperuserSelfDeletionError(Exception):
    """Raise when a superuser tries to delete itself."""

    message = "Super users are not allowed to delete themselves."

    def __str__(self) -> str:
        """Return the default human-readable error message."""
        return SuperuserSelfDeletionError.message
