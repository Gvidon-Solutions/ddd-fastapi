"""Codex job repository tests."""

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.codex_job.entities import CodexJob
from app.domain.codex_job.value_objects import CodexJobPrompt, CodexJobStatus
from app.infrastructure.sqlmodel.codex_job import new_codex_job_repository

pytestmark = pytest.mark.anyio


async def test_codex_job_repository_saves_and_finds_job(
    db_session: AsyncSession,
) -> None:
    # Arrange
    repository = new_codex_job_repository(db_session)
    codex_job = CodexJob.create(CodexJobPrompt("Review repository"))
    codex_job.attach_backend_job("backend-job-id")

    # Act
    await repository.save(codex_job)
    await db_session.commit()
    found = await repository.find_by_id(codex_job.id)

    # Assert
    assert found == codex_job
    assert found is not None
    assert found.backend_job_id == "backend-job-id"


async def test_codex_job_repository_updates_job(
    db_session: AsyncSession,
) -> None:
    # Arrange
    repository = new_codex_job_repository(db_session)
    codex_job = CodexJob.create(CodexJobPrompt("Review repository"))
    await repository.save(codex_job)
    await db_session.commit()

    # Act
    codex_job.start()
    await repository.save(codex_job)
    await db_session.commit()
    found = await repository.find_by_id(codex_job.id)

    # Assert
    assert found is not None
    assert found.status == CodexJobStatus.RUNNING
