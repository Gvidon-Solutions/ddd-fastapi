"""FastDepends dependencies for ARQ workers."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.domain.codex_job.repositories import CodexJobRepository
from app.infrastructure.arq.codex_job_runner import new_codex_job_runner
from app.infrastructure.sqlmodel.codex_job import new_codex_job_repository
from app.usecase.codex_job import CodexJobRunner


@dataclass(frozen=True)
class CodexJobWorkerDependencies:
    """Dependencies required to execute one Codex job."""

    session: AsyncSession
    repository: CodexJobRepository
    runner: CodexJobRunner


async def get_codex_job_worker_dependencies() -> AsyncGenerator[
    CodexJobWorkerDependencies
]:
    """Yield ARQ job-scoped Codex job dependencies."""
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    async with AsyncSession(engine) as session:
        try:
            yield CodexJobWorkerDependencies(
                session=session,
                repository=new_codex_job_repository(session),
                runner=new_codex_job_runner(),
            )
        except Exception:
            await session.rollback()
            raise
