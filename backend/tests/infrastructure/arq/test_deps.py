"""ARQ FastDepends dependency tests."""

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infrastructure.arq.deps import CodexJobWorkerDependencies
from app.infrastructure.codex import new_codex_job_runner
from app.infrastructure.sqlmodel.codex_job import new_codex_job_repository
from app.infrastructure.sqlmodel.codex_job.codex_job_repository import (
    CodexJobRepositoryImpl,
)

pytestmark = pytest.mark.anyio


async def test_codex_job_worker_dependencies_share_repository_session(
    db_session: AsyncSession,
) -> None:
    # Arrange
    repository = new_codex_job_repository(db_session)

    # Act
    dependencies = CodexJobWorkerDependencies(
        session=db_session,
        repository=repository,
        runner=new_codex_job_runner(),
    )

    # Assert
    assert isinstance(dependencies.repository, CodexJobRepositoryImpl)
    assert dependencies.repository.session is dependencies.session
