"""FastAPI dependencies shared by routes."""

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError

from app.config import settings
from app.domain.user.entities import User
from app.domain.user.exceptions import (
    InactiveUserError,
    UserAccessDeniedError,
    UserNotFoundError,
)
from app.domain.user.repositories import UserRepository
from app.domain.user.value_objects import UserId
from app.infrastructure.di import get_user_repository
from app.infrastructure.security import ALGORITHM
from app.presentation.api.common import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token",
)

TokenDep = Annotated[str, Depends(reusable_oauth2)]


async def get_current_user(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    token: TokenDep,
) -> User:
    """Decode the token and return the active domain user."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            raise UserNotFoundError
        user_id = UserId(UUID(token_data.sub))
    except (InvalidTokenError, ValidationError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user = await user_repository.find_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=UserNotFoundError.message)
    if not user.is_active:
        raise HTTPException(status_code=400, detail=InactiveUserError.message)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_active_superuser(current_user: CurrentUser) -> User:
    """Return the current user when it has admin privileges."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail=UserAccessDeniedError.message,
        )
    return current_user
