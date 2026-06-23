"""FastDepends dependencies for ARQ job tasks."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass

from fast_depends import Depends
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.domain.job import JobArtifactRepository, JobEventRepository, JobRepository
from app.infrastructure.artifact_storage import new_filesystem_artifact_storage
from app.infrastructure.clock import new_system_clock
from app.infrastructure.sqlmodel.job import (
    new_job_artifact_repository,
    new_job_event_repository,
    new_job_repository,
)
from app.usecase.job import ArtifactStorage, Clock


@dataclass(frozen=True)
class JobTaskTransaction:
    """Commit or roll back ARQ task persistence."""

    session: AsyncSession

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        await self.session.rollback()


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Yield an ARQ task-scoped SQLModel session."""
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    async with AsyncSession(engine) as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await engine.dispose()


def get_job_repository(
    session: AsyncSession = Depends(get_session),
) -> JobRepository:
    """Provide a job repository."""
    return new_job_repository(session)


def get_job_artifact_repository(
    session: AsyncSession = Depends(get_session),
) -> JobArtifactRepository:
    """Provide a job artifact repository."""
    return new_job_artifact_repository(session)


def get_job_event_repository(
    session: AsyncSession = Depends(get_session),
) -> JobEventRepository:
    """Provide a job event repository."""
    return new_job_event_repository(session)


def get_artifact_storage() -> ArtifactStorage:
    """Provide artifact storage."""
    return new_filesystem_artifact_storage()


def get_clock() -> Clock:
    """Provide a clock."""
    return new_system_clock()


def get_job_task_transaction(
    session: AsyncSession = Depends(get_session),
) -> JobTaskTransaction:
    """Provide an ARQ task transaction."""
    return JobTaskTransaction(session=session)
