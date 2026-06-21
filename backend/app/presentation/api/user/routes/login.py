"""Authentication and password recovery routes."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.config import settings
from app.domain.user.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from app.domain.user.repositories import UserRepository
from app.domain.user.value_objects import EmailAddress, PasswordHash
from app.infrastructure.di import (
    get_authenticate_user_use_case,
    get_password_hasher,
    get_user_repository,
)
from app.infrastructure.email import generate_reset_password_email, send_email
from app.infrastructure.security import (
    create_access_token,
    generate_password_reset_token,
    verify_password_reset_token,
)
from app.presentation.api.common import Message, NewPassword, Token
from app.presentation.api.common.deps import CurrentUser, get_current_active_superuser
from app.presentation.api.user import UserPublic
from app.usecase.user import AuthenticateUserUseCase
from app.usecase.user.ports import PasswordHasher

router = APIRouter(tags=["login"])


@router.post("/login/access-token")
async def login_access_token(
    use_case: Annotated[
        AuthenticateUserUseCase,
        Depends(get_authenticate_user_use_case),
    ],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """OAuth2 compatible token login."""
    try:
        user = await use_case.execute(
            email=EmailAddress(form_data.username),
            plain_password=form_data.password,
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=400,
            detail=error.message,
        ) from error
    except InactiveUserError as error:
        raise HTTPException(status_code=400, detail=error.message) from error

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=create_access_token(
            user.id.value,
            expires_delta=access_token_expires,
        ),
    )


@router.post("/login/test-token", response_model=UserPublic)
async def test_token(current_user: CurrentUser) -> UserPublic:
    """Test an access token."""
    return UserPublic.from_entity(current_user)


@router.post("/password-recovery/{email}")
async def recover_password(
    email: str,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> Message:
    """Send a password recovery email when the user exists."""
    try:
        user = await user_repository.find_by_email(EmailAddress(email))
    except ValueError:
        user = None

    if user:
        password_reset_token = generate_password_reset_token(email=email)
        email_data = generate_reset_password_email(
            email_to=user.email.value,
            email=email,
            token=password_reset_token,
        )
        send_email(
            email_to=user.email.value,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return Message(
        message="If that email is registered, we sent a password recovery link",
    )


@router.post("/reset-password/")
async def reset_password(
    body: NewPassword,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    password_hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
) -> Message:
    """Reset a password using a reset token."""
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = await user_repository.find_by_email(EmailAddress(email))
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Invalid token")

    user.update_password_hash(
        PasswordHash(password_hasher.hash_password(body.new_password).value)
    )
    await user_repository.save(user)
    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
async def recover_password_html_content(
    email: str,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> HTMLResponse:
    """Return password recovery email HTML for admins."""
    user = await user_repository.find_by_email(EmailAddress(email))
    if user is None:
        raise HTTPException(
            status_code=404,
            detail=UserNotFoundError.message,
        )

    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email.value,
        email=email,
        token=password_reset_token,
    )
    return HTMLResponse(
        content=email_data.html_content,
        headers={"subject:": email_data.subject},
    )
