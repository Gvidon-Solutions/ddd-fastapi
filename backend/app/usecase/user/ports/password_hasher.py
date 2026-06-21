"""Define the password hashing port."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.user.value_objects import PasswordHash


@dataclass(frozen=True)
class PasswordVerificationResult:
    """Represent a password verification result."""

    verified: bool
    updated_hash: PasswordHash | None = None


class PasswordHasher(ABC):
    """Provide password hashing and verification operations."""

    @abstractmethod
    def hash_password(self, plain_password: str) -> PasswordHash:
        """Return the hash for a plain-text password."""

    @abstractmethod
    def verify_password(
        self,
        plain_password: str,
        hashed_password: PasswordHash,
    ) -> PasswordVerificationResult:
        """Verify a plain-text password against a stored hash."""
