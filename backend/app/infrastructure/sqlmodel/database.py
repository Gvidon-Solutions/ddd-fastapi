"""Database bootstrap helpers."""

from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.domain.user.value_objects import EmailAddress
from app.infrastructure.di.injection import engine
from app.infrastructure.security import new_password_hasher
from app.infrastructure.sqlmodel.event import EventDTO, JobEventLinkDTO
from app.infrastructure.sqlmodel.item import ItemDTO
from app.infrastructure.sqlmodel.job import FileDTO, InitiatorDTO, JobDTO, JobFileDTO
from app.infrastructure.sqlmodel.user import UserDTO, new_user_repository
from app.usecase.user import new_create_user_use_case

__all__ = (
    "ItemDTO",
    "EventDTO",
    "JobEventLinkDTO",
    "FileDTO",
    "InitiatorDTO",
    "JobDTO",
    "JobFileDTO",
    "SQLModel",
    "UserDTO",
    "engine",
    "init_db",
)


async def init_db(session: AsyncSession) -> None:
    """Initialize required data."""
    user_repository = new_user_repository(session)
    user = await user_repository.find_by_email(
        EmailAddress(str(settings.FIRST_SUPERUSER))
    )
    if user is not None:
        return

    create_user = new_create_user_use_case(
        user_repository=user_repository,
        password_hasher=new_password_hasher(),
    )
    await create_user.execute(
        email=EmailAddress(str(settings.FIRST_SUPERUSER)),
        plain_password=settings.FIRST_SUPERUSER_PASSWORD,
        is_superuser=True,
    )
