"""Define the password hash value object."""

from dataclasses import dataclass

PASSWORD_HASH_REQUIRED_ERROR_MESSAGE = "Password hash is required"


@dataclass(frozen=True)
class PasswordHash:
    """Represent a persisted password hash."""

    value: str

    def __post_init__(self) -> None:
        """Validate the stored password hash."""
        if not self.value:
            raise ValueError(PASSWORD_HASH_REQUIRED_ERROR_MESSAGE)

    def __str__(self) -> str:
        """Return the wrapped password hash string."""
        return self.value
