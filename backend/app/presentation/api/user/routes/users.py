"""User HTTP routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.domain.user.exceptions import (
    EmailAlreadyExistsError,
    IncorrectPasswordError,
    PasswordReuseError,
    SuperuserSelfDeletionError,
    UserAccessDeniedError,
    UserNotFoundError,
)
from app.domain.user.value_objects import EmailAddress, FullName, UserId
from app.infrastructure.di import (
    get_create_user_use_case,
    get_delete_current_user_use_case,
    get_delete_user_use_case,
    get_find_user_by_id_use_case,
    get_find_users_use_case,
    get_register_user_use_case,
    get_update_current_user_password_use_case,
    get_update_current_user_use_case,
    get_update_user_use_case,
)
from app.infrastructure.email import generate_new_account_email, send_email
from app.presentation.api.common import Message
from app.presentation.api.common.deps import CurrentUser, get_current_active_superuser
from app.presentation.api.user import (
    UpdatePassword,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.usecase.user import (
    CreateUserUseCase,
    DeleteCurrentUserUseCase,
    DeleteUserUseCase,
    FindUserByIdUseCase,
    FindUsersUseCase,
    RegisterUserUseCase,
    UpdateCurrentUserPasswordUseCase,
    UpdateCurrentUserUseCase,
    UpdateUserUseCase,
)

router = APIRouter(prefix="/users", tags=["users"])


def _full_name(value: str | None) -> FullName | None:
    """Build an optional full-name value object."""
    return FullName(value) if value else None


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
def read_users(
    current_user: CurrentUser,
    use_case: Annotated[FindUsersUseCase, Depends(get_find_users_use_case)],
    skip: int = 0,
    limit: int = 100,
) -> UsersPublic:
    """Retrieve users."""
    try:
        result = use_case.execute(current_user, offset=skip, limit=limit)
    except UserAccessDeniedError as error:
        raise HTTPException(
            status_code=403,
            detail=error.message,
        ) from error
    return UsersPublic(
        data=[UserPublic.from_entity(user) for user in result.data],
        count=result.count,
    )


@router.post(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def create_user(
    use_case: Annotated[CreateUserUseCase, Depends(get_create_user_use_case)],
    user_in: UserCreate,
) -> UserPublic:
    """Create a new user as an administrator."""
    try:
        user = use_case.execute(
            email=EmailAddress(str(user_in.email)),
            plain_password=user_in.password,
            full_name=_full_name(user_in.full_name),
            is_active=user_in.is_active,
            is_superuser=user_in.is_superuser,
        )
    except EmailAlreadyExistsError as error:
        raise HTTPException(
            status_code=400,
            detail=error.message,
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=str(user_in.email),
            username=str(user_in.email),
            password=user_in.password,
        )
        send_email(
            email_to=str(user_in.email),
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return UserPublic.from_entity(user)


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    current_user: CurrentUser,
    use_case: Annotated[
        UpdateCurrentUserUseCase,
        Depends(get_update_current_user_use_case),
    ],
    user_in: UserUpdateMe,
) -> UserPublic:
    """Update the current user's profile."""
    try:
        user = use_case.execute(
            current_user=current_user,
            email=EmailAddress(str(user_in.email)) if user_in.email else None,
            full_name=_full_name(user_in.full_name)
            if "full_name" in user_in.model_fields_set
            else None,
        )
    except EmailAlreadyExistsError as error:
        raise HTTPException(
            status_code=409,
            detail=error.message,
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return UserPublic.from_entity(user)


@router.patch("/me/password", response_model=Message)
def update_password_me(
    current_user: CurrentUser,
    use_case: Annotated[
        UpdateCurrentUserPasswordUseCase,
        Depends(get_update_current_user_password_use_case),
    ],
    body: UpdatePassword,
) -> Message:
    """Update the current user's password."""
    try:
        use_case.execute(
            current_user=current_user,
            current_plain_password=body.current_password,
            new_plain_password=body.new_password,
        )
    except IncorrectPasswordError as error:
        raise HTTPException(status_code=400, detail=error.message) from error
    except PasswordReuseError as error:
        raise HTTPException(
            status_code=400,
            detail=error.message,
        ) from error
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> UserPublic:
    """Return the current user."""
    return UserPublic.from_entity(current_user)


@router.delete("/me", response_model=Message)
def delete_user_me(
    current_user: CurrentUser,
    use_case: Annotated[
        DeleteCurrentUserUseCase,
        Depends(get_delete_current_user_use_case),
    ],
) -> Message:
    """Delete the current user."""
    try:
        use_case.execute(current_user)
    except SuperuserSelfDeletionError as error:
        raise HTTPException(
            status_code=403,
            detail=error.message,
        ) from error
    return Message(message="User deleted successfully")


@router.post("/signup", response_model=UserPublic)
def register_user(
    use_case: Annotated[RegisterUserUseCase, Depends(get_register_user_use_case)],
    user_in: UserRegister,
) -> UserPublic:
    """Create a regular user without authentication."""
    try:
        user = use_case.execute(
            email=EmailAddress(str(user_in.email)),
            plain_password=user_in.password,
            full_name=_full_name(user_in.full_name),
        )
    except EmailAlreadyExistsError as error:
        raise HTTPException(
            status_code=400,
            detail=error.message,
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return UserPublic.from_entity(user)


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    current_user: CurrentUser,
    use_case: Annotated[FindUserByIdUseCase, Depends(get_find_user_by_id_use_case)],
    user_id: uuid.UUID,
) -> UserPublic:
    """Get a specific user by id."""
    try:
        user = use_case.execute(UserId(user_id), current_user)
    except UserAccessDeniedError as error:
        raise HTTPException(
            status_code=403,
            detail=error.message,
        ) from error
    except UserNotFoundError as error:
        raise HTTPException(status_code=404, detail=error.message) from error
    return UserPublic.from_entity(user)


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def update_user(
    current_user: CurrentUser,
    use_case: Annotated[UpdateUserUseCase, Depends(get_update_user_use_case)],
    user_id: uuid.UUID,
    user_in: UserUpdate,
) -> UserPublic:
    """Update a user as an administrator."""
    try:
        user = use_case.execute(
            current_user=current_user,
            user_id=UserId(user_id),
            email=EmailAddress(str(user_in.email)) if user_in.email else None,
            full_name=_full_name(user_in.full_name)
            if "full_name" in user_in.model_fields_set
            else None,
            plain_password=user_in.password,
            is_active=user_in.is_active,
            is_superuser=user_in.is_superuser,
        )
    except UserNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=error.message,
        ) from error
    except EmailAlreadyExistsError as error:
        raise HTTPException(
            status_code=409,
            detail=error.message,
        ) from error
    except UserAccessDeniedError as error:
        raise HTTPException(
            status_code=403,
            detail=error.message,
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return UserPublic.from_entity(user)


@router.delete(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def delete_user(
    current_user: CurrentUser,
    use_case: Annotated[DeleteUserUseCase, Depends(get_delete_user_use_case)],
    user_id: uuid.UUID,
) -> Message:
    """Delete a user as an administrator."""
    try:
        use_case.execute(current_user, UserId(user_id))
    except UserNotFoundError as error:
        raise HTTPException(status_code=404, detail=error.message) from error
    except SuperuserSelfDeletionError as error:
        raise HTTPException(
            status_code=403,
            detail=error.message,
        ) from error
    except UserAccessDeniedError as error:
        raise HTTPException(
            status_code=403,
            detail=error.message,
        ) from error
    return Message(message="User deleted successfully")
