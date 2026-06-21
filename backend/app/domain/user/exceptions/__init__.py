"""Expose user-specific domain exceptions."""

from __future__ import annotations

from .email_already_exists_error import EmailAlreadyExistsError
from .inactive_user_error import InactiveUserError
from .incorrect_password_error import IncorrectPasswordError
from .invalid_credentials_error import InvalidCredentialsError
from .password_reuse_error import PasswordReuseError
from .superuser_self_deletion_error import SuperuserSelfDeletionError
from .user_access_denied_error import UserAccessDeniedError
from .user_not_found_error import UserNotFoundError

__all__ = (
    "EmailAlreadyExistsError",
    "IncorrectPasswordError",
    "InactiveUserError",
    "InvalidCredentialsError",
    "PasswordReuseError",
    "SuperuserSelfDeletionError",
    "UserAccessDeniedError",
    "UserNotFoundError",
)
