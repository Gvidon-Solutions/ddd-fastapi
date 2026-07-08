"""SQLModel implementation of the user repository."""

from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.user.entities import User
from app.domain.user.repositories import UserRepository
from app.domain.user.value_objects import EmailAddress, UserId
from app.infrastructure.sqlmodel.user.user_dto import UserDTO


class UserRepositoryImpl(UserRepository):
    """Persist user entities with SQLModel."""

    def __init__(self, session: AsyncSession):
        """Store the active SQLModel session."""
        self.session = session

    async def save(self, user: User) -> None:
        """Insert or update a user."""
        user_dto = UserDTO.from_entity(user)
        existing_user = await self.session.get(UserDTO, user.id)
        if existing_user is None:
            self.session.add(user_dto)
            return

        existing_user.email = user_dto.email
        existing_user.hashed_password = user_dto.hashed_password
        existing_user.full_name = user_dto.full_name
        existing_user.is_active = user_dto.is_active
        existing_user.is_superuser = user_dto.is_superuser
        existing_user.created_at = user_dto.created_at
        self.session.add(existing_user)

    async def find_by_id(self, user_id: UserId) -> User | None:
        """Return a user by ID."""
        user = await self.session.get(UserDTO, user_id)
        return user.to_entity() if user else None

    async def find_by_email(self, email: EmailAddress) -> User | None:
        """Return a user by email."""
        statement = select(UserDTO).where(UserDTO.email == email.value)
        result = await self.session.exec(statement)
        user = result.first()
        return user.to_entity() if user else None

    async def find_all(self, offset: int = 0, limit: int = 100) -> list[User]:
        """Return users ordered newest first."""
        statement = (
            select(UserDTO)
            .order_by(col(UserDTO.created_at).desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.exec(statement)
        return [user.to_entity() for user in result.all()]

    async def count(self) -> int:
        """Return the total user count."""
        statement = select(func.count()).select_from(UserDTO)
        result = await self.session.exec(statement)
        return result.one()

    async def delete(self, user_id: UserId) -> None:
        """Delete a user by ID."""
        user = await self.session.get(UserDTO, user_id)
        if user is not None:
            await self.session.delete(user)


def new_user_repository(session: AsyncSession) -> UserRepository:
    """Create a user repository bound to the active session."""
    return UserRepositoryImpl(session)
