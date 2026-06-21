"""Define the full name value object."""

from dataclasses import dataclass

MAX_FULL_NAME_LENGTH = 255
FULL_NAME_TOO_LONG_ERROR_MESSAGE = "Full name must be 255 characters or less"


@dataclass(frozen=True)
class FullName:
    """Represent a user's optional display name."""

    value: str

    def __post_init__(self) -> None:
        """Validate full name constraints."""
        if len(self.value) > MAX_FULL_NAME_LENGTH:
            raise ValueError(FULL_NAME_TOO_LONG_ERROR_MESSAGE)

    def __str__(self) -> str:
        """Return the wrapped full name string."""
        return self.value
