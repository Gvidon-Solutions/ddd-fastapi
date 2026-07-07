"""ARQ worker dependency wiring."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import Job, JobEvent, JobFile
from app.infrastructure.sqlmodel.job.job_repository import JobRepositoryImpl

ARQ_DB_ENGINE = "db_engine"
ARQ_FILE_STORAGE = "file_storage"
ARQ_CODEX_AUTHENTICATOR = "codex_authenticator"
ARQ_CODEX_AUTH_SESSION_REPOSITORY = "codex_auth_session_repository"


class AutocommitJobRepository(JobRepositoryImpl):
    """Job repository that commits every write for ARQ progress visibility."""

    async def create(self, job: Job) -> None:
        """Create and commit a job."""
        await super().create(job)
        await self.session.commit()

    async def save(self, job: Job) -> None:
        """Save and commit a job."""
        await super().save(job)
        await self.session.commit()

    async def add_file(self, job_file: JobFile) -> None:
        """Associate a file and commit."""
        await super().add_file(job_file)
        await self.session.commit()

    async def append_event(self, job_id: UUID, event: JobEvent) -> None:
        """Append an event and commit."""
        await super().append_event(job_id, event)
        await self.session.commit()

    async def try_mark_running(self, *args, **kwargs) -> bool:
        """Mark running and commit."""
        result = await super().try_mark_running(*args, **kwargs)
        await self.session.commit()
        return result

    async def try_mark_succeeded(self, *args, **kwargs) -> bool:
        """Mark succeeded and commit."""
        result = await super().try_mark_succeeded(*args, **kwargs)
        await self.session.commit()
        return result

    async def try_mark_failed(self, *args, **kwargs) -> bool:
        """Mark failed and commit."""
        result = await super().try_mark_failed(*args, **kwargs)
        await self.session.commit()
        return result

    async def try_mark_cancelled(self, *args, **kwargs) -> bool:
        """Mark cancelled and commit."""
        result = await super().try_mark_cancelled(*args, **kwargs)
        await self.session.commit()
        return result


def get_arq_db_engine(ctx: dict[str, Any]) -> AsyncEngine:
    """Return the ARQ worker database engine."""
    return ctx[ARQ_DB_ENGINE]


def new_arq_job_repository(session: AsyncSession) -> AutocommitJobRepository:
    """Create an ARQ job repository."""
    return AutocommitJobRepository(session)
