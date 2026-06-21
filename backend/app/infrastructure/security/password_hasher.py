"""Password hashing adapter for user use cases."""

from pwdlib import PasswordHash as PwdlibPasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.domain.user.value_objects import PasswordHash
from app.usecase.user.ports import PasswordHasher, PasswordVerificationResult

password_hash = PwdlibPasswordHash((Argon2Hasher(), BcryptHasher()))


class PasswordHasherImpl(PasswordHasher):
    """Use the configured pwdlib hashers behind the password port."""

    def hash_password(self, plain_password: str) -> PasswordHash:
        """Hash a plain-text password."""
        return PasswordHash(password_hash.hash(plain_password))

    def verify_password(
        self,
        plain_password: str,
        hashed_password: PasswordHash,
    ) -> PasswordVerificationResult:
        """Verify a plain-text password against a stored hash."""
        verified, updated_hash = password_hash.verify_and_update(
            plain_password,
            hashed_password.value,
        )
        return PasswordVerificationResult(
            verified=verified,
            updated_hash=PasswordHash(updated_hash) if updated_hash else None,
        )


def new_password_hasher() -> PasswordHasher:
    """Create a password hashing adapter."""
    return PasswordHasherImpl()
