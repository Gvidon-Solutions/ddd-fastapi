"""Define the User aggregate root."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.user.exceptions import SuperuserSelfDeletionError
from app.domain.user.value_objects import EmailAddress, FullName, PasswordHash, UserId


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


@dataclass(eq=False)
class User:
    """Represent an account that can own resources and authenticate."""

    id: UserId
    email: EmailAddress
    hashed_password: PasswordHash
    full_name: FullName | None = None
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = field(default_factory=_utc_now)

    def __hash__(self) -> int:
        """Return a hash value based on the entity identity."""
        return hash(self.id)

    def __eq__(self, obj: object) -> bool:
        """Compare users by identifier."""
        if isinstance(obj, User):
            return self.id == obj.id
        return False

    def update_email(self, email: EmailAddress) -> None:
        """Replace the user's email address."""
        self.email = email

    def update_full_name(self, full_name: FullName | None) -> None:
        """Replace the user's display name."""
        self.full_name = full_name

    def update_password_hash(self, hashed_password: PasswordHash) -> None:
        """Replace the user's stored password hash."""
        self.hashed_password = hashed_password

    def activate(self) -> None:
        """Mark the user as active."""
        self.is_active = True

    def deactivate(self) -> None:
        """Mark the user as inactive."""
        self.is_active = False

    def grant_superuser(self) -> None:
        """Grant administrative privileges."""
        self.is_superuser = True

    def revoke_superuser(self) -> None:
        """Revoke administrative privileges."""
        self.is_superuser = False

    def ensure_can_delete_self(self) -> None:
        """Raise when the user is not allowed to delete itself."""
        if self.is_superuser:
            raise SuperuserSelfDeletionError

    @staticmethod
    def create(
        email: EmailAddress,
        hashed_password: PasswordHash,
        full_name: FullName | None = None,
        *,
        is_superuser: bool = False,
    ) -> "User":
        """Create a new user with a generated identifier."""
        return User(
            id=UserId.generate(),
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_superuser=is_superuser,
        )
