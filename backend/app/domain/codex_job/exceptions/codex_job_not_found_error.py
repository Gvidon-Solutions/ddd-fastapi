"""Codex job not found error."""


class CodexJobNotFoundError(Exception):
    """Raised when a Codex job does not exist."""

    message = "Codex job not found"

    def __str__(self) -> str:
        """Return a stable error message."""
        return self.message
