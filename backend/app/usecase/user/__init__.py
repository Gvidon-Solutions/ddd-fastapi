"""Expose user application use cases."""

from __future__ import annotations

from .authenticate_user_use_case import (
    AuthenticateUserUseCase,
    new_authenticate_user_use_case,
)
from .create_user_use_case import CreateUserUseCase, new_create_user_use_case
from .delete_current_user_use_case import (
    DeleteCurrentUserUseCase,
    new_delete_current_user_use_case,
)
from .delete_user_use_case import DeleteUserUseCase, new_delete_user_use_case
from .find_user_by_id_use_case import (
    FindUserByIdUseCase,
    new_find_user_by_id_use_case,
)
from .find_users_use_case import (
    FindUsersResult,
    FindUsersUseCase,
    new_find_users_use_case,
)
from .register_user_use_case import RegisterUserUseCase, new_register_user_use_case
from .update_current_user_password_use_case import (
    UpdateCurrentUserPasswordUseCase,
    new_update_current_user_password_use_case,
)
from .update_current_user_use_case import (
    UpdateCurrentUserUseCase,
    new_update_current_user_use_case,
)
from .update_user_use_case import UpdateUserUseCase, new_update_user_use_case

__all__ = (
    "AuthenticateUserUseCase",
    "CreateUserUseCase",
    "DeleteCurrentUserUseCase",
    "DeleteUserUseCase",
    "FindUserByIdUseCase",
    "FindUsersResult",
    "FindUsersUseCase",
    "RegisterUserUseCase",
    "UpdateCurrentUserPasswordUseCase",
    "UpdateCurrentUserUseCase",
    "UpdateUserUseCase",
    "new_authenticate_user_use_case",
    "new_create_user_use_case",
    "new_delete_current_user_use_case",
    "new_delete_user_use_case",
    "new_find_user_by_id_use_case",
    "new_find_users_use_case",
    "new_register_user_use_case",
    "new_update_current_user_password_use_case",
    "new_update_current_user_use_case",
    "new_update_user_use_case",
)
