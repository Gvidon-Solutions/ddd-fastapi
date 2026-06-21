"""Define the email address value object."""

from dataclasses import dataclass

MAX_EMAIL_LENGTH = 255
EMAIL_REQUIRED_ERROR_MESSAGE = "Email is required"
EMAIL_TOO_LONG_ERROR_MESSAGE = "Email must be 255 characters or less"
EMAIL_INVALID_ERROR_MESSAGE = "Email must contain a local part and a domain"


@dataclass(frozen=True)
class EmailAddress:
    """Represent a user email address."""

    value: str

    def __post_init__(self) -> None:
        """Validate basic email constraints."""
        if not self.value:
            raise ValueError(EMAIL_REQUIRED_ERROR_MESSAGE)
        if len(self.value) > MAX_EMAIL_LENGTH:
            raise ValueError(EMAIL_TOO_LONG_ERROR_MESSAGE)
        local_part, separator, domain = self.value.partition("@")
        if not local_part or separator != "@" or not domain or "." not in domain:
            raise ValueError(EMAIL_INVALID_ERROR_MESSAGE)

    def __str__(self) -> str:
        """Return the wrapped email string."""
        return self.value
