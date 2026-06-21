"""Define the item title value object."""

from dataclasses import dataclass

MAX_TITLE_LENGTH = 255
TITLE_REQUIRED_ERROR_MESSAGE = "Title is required"
TITLE_TOO_LONG_ERROR_MESSAGE = "Title must be 255 characters or less"


@dataclass(frozen=True)
class ItemTitle:
    """Represent an item title."""

    value: str

    def __post_init__(self) -> None:
        """Validate item title constraints."""
        if not self.value:
            raise ValueError(TITLE_REQUIRED_ERROR_MESSAGE)
        if len(self.value) > MAX_TITLE_LENGTH:
            raise ValueError(TITLE_TOO_LONG_ERROR_MESSAGE)

    def __str__(self) -> str:
        """Return the wrapped title string."""
        return self.value
