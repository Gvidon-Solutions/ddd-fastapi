"""Define the item description value object."""

from dataclasses import dataclass

MAX_DESCRIPTION_LENGTH = 255
DESCRIPTION_TOO_LONG_ERROR_MESSAGE = "Description must be 255 characters or less"


@dataclass(frozen=True)
class ItemDescription:
    """Represent an optional item description."""

    value: str

    def __post_init__(self) -> None:
        """Validate item description constraints."""
        if len(self.value) > MAX_DESCRIPTION_LENGTH:
            raise ValueError(DESCRIPTION_TOO_LONG_ERROR_MESSAGE)

    def __str__(self) -> str:
        """Return the wrapped description string."""
        return self.value
