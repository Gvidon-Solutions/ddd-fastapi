"""FastAPI dependency wiring for repositories and use cases."""

from collections.abc import Generator

from fastapi import Depends
from sqlmodel import Session, create_engine

from app.config import settings
from app.domain.item.repositories import ItemRepository
from app.domain.user.repositories import UserRepository
from app.infrastructure.security import new_password_hasher
from app.infrastructure.sqlmodel.item import new_item_repository
from app.infrastructure.sqlmodel.user import new_user_repository
from app.usecase.item import (
    CreateItemUseCase,
    DeleteItemUseCase,
    FindItemByIdUseCase,
    FindItemsUseCase,
    UpdateItemUseCase,
    new_create_item_use_case,
    new_delete_item_use_case,
    new_find_item_by_id_use_case,
    new_find_items_use_case,
    new_update_item_use_case,
)
from app.usecase.user import (
    AuthenticateUserUseCase,
    CreateUserUseCase,
    DeleteCurrentUserUseCase,
    DeleteUserUseCase,
    FindUserByIdUseCase,
    FindUsersUseCase,
    RegisterUserUseCase,
    UpdateCurrentUserPasswordUseCase,
    UpdateCurrentUserUseCase,
    UpdateUserUseCase,
    new_authenticate_user_use_case,
    new_create_user_use_case,
    new_delete_current_user_use_case,
    new_delete_user_use_case,
    new_find_user_by_id_use_case,
    new_find_users_use_case,
    new_register_user_use_case,
    new_update_current_user_password_use_case,
    new_update_current_user_use_case,
    new_update_user_use_case,
)
from app.usecase.user.ports import PasswordHasher

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def get_session() -> Generator[Session]:
    """Yield a request-scoped SQLModel session."""
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_item_repository(session: Session = Depends(get_session)) -> ItemRepository:
    """Provide an item repository."""
    return new_item_repository(session)


def get_user_repository(session: Session = Depends(get_session)) -> UserRepository:
    """Provide a user repository."""
    return new_user_repository(session)


def get_password_hasher() -> PasswordHasher:
    """Provide a password hasher."""
    return new_password_hasher()


def get_authenticate_user_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> AuthenticateUserUseCase:
    """Provide the authenticate-user use case."""
    return new_authenticate_user_use_case(user_repository, password_hasher)


def get_create_item_use_case(
    item_repository: ItemRepository = Depends(get_item_repository),
) -> CreateItemUseCase:
    """Provide the create-item use case."""
    return new_create_item_use_case(item_repository)


def get_find_items_use_case(
    item_repository: ItemRepository = Depends(get_item_repository),
) -> FindItemsUseCase:
    """Provide the list-items use case."""
    return new_find_items_use_case(item_repository)


def get_find_item_by_id_use_case(
    item_repository: ItemRepository = Depends(get_item_repository),
) -> FindItemByIdUseCase:
    """Provide the find-item-by-id use case."""
    return new_find_item_by_id_use_case(item_repository)


def get_update_item_use_case(
    item_repository: ItemRepository = Depends(get_item_repository),
) -> UpdateItemUseCase:
    """Provide the update-item use case."""
    return new_update_item_use_case(item_repository)


def get_delete_item_use_case(
    item_repository: ItemRepository = Depends(get_item_repository),
) -> DeleteItemUseCase:
    """Provide the delete-item use case."""
    return new_delete_item_use_case(item_repository)


def get_create_user_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> CreateUserUseCase:
    """Provide the admin create-user use case."""
    return new_create_user_use_case(user_repository, password_hasher)


def get_register_user_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> RegisterUserUseCase:
    """Provide the public registration use case."""
    return new_register_user_use_case(user_repository, password_hasher)


def get_find_users_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
) -> FindUsersUseCase:
    """Provide the list-users use case."""
    return new_find_users_use_case(user_repository)


def get_find_user_by_id_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
) -> FindUserByIdUseCase:
    """Provide the find-user-by-id use case."""
    return new_find_user_by_id_use_case(user_repository)


def get_update_current_user_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
) -> UpdateCurrentUserUseCase:
    """Provide the current-user update use case."""
    return new_update_current_user_use_case(user_repository)


def get_update_current_user_password_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> UpdateCurrentUserPasswordUseCase:
    """Provide the current-user password update use case."""
    return new_update_current_user_password_use_case(user_repository, password_hasher)


def get_update_user_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> UpdateUserUseCase:
    """Provide the admin update-user use case."""
    return new_update_user_use_case(user_repository, password_hasher)


def get_delete_current_user_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
) -> DeleteCurrentUserUseCase:
    """Provide the current-user delete use case."""
    return new_delete_current_user_use_case(user_repository)


def get_delete_user_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
) -> DeleteUserUseCase:
    """Provide the admin delete-user use case."""
    return new_delete_user_use_case(user_repository)
