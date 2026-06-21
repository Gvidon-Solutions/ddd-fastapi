"""Codex job use case tests."""

import pytest

from app.domain.codex_job.entities import CodexJob
from app.domain.codex_job.exceptions import CodexJobNotFoundError
from app.domain.codex_job.repositories import CodexJobRepository
from app.domain.codex_job.value_objects import (
    CodexJobId,
    CodexJobPrompt,
    CodexJobStatus,
)
from app.usecase.codex_job import (
    CodexJobRunner,
    CodexJobStarter,
    new_abort_codex_job_use_case,
    new_enqueue_codex_job_use_case,
    new_execute_codex_job_use_case,
    new_get_status_codex_job_use_case,
)

pytestmark = pytest.mark.anyio


class FakeCodexJobRepository(CodexJobRepository):
    """Fake Codex job repository."""

    def __init__(self) -> None:
        """Initialize fake storage."""
        self.jobs: dict[CodexJobId, CodexJob] = {}

    async def save(self, codex_job: CodexJob) -> None:
        """Save a fake job."""
        self.jobs[codex_job.id] = codex_job

    async def find_by_id(self, codex_job_id: CodexJobId) -> CodexJob | None:
        """Find a fake job."""
        return self.jobs.get(codex_job_id)


class FakeCodexJobStarter(CodexJobStarter):
    """Fake Codex job starter."""

    def __init__(self) -> None:
        """Initialize fake state."""
        self.started_job_id: CodexJobId | None = None
        self.aborted_backend_job_id: str | None = None

    async def start(self, codex_job_id: CodexJobId) -> str:
        """Start a fake backend job."""
        self.started_job_id = codex_job_id
        return "backend-job-id"

    async def abort(self, backend_job_id: str) -> None:
        """Abort a fake backend job."""
        self.aborted_backend_job_id = backend_job_id


class FakeCodexJobRunner(CodexJobRunner):
    """Fake Codex job runner."""

    async def execute(self, codex_job: CodexJob) -> str:
        """Return a fake result."""
        return f"done: {codex_job.prompt.value}"


async def test_enqueue_codex_job_use_case_persists_and_starts_job() -> None:
    # Arrange
    repository = FakeCodexJobRepository()
    starter = FakeCodexJobStarter()
    use_case = new_enqueue_codex_job_use_case(repository, starter)

    # Act
    codex_job = await use_case.execute(CodexJobPrompt("Review repository"))

    # Assert
    assert codex_job.status == CodexJobStatus.QUEUED
    assert codex_job.backend_job_id == "backend-job-id"
    assert starter.started_job_id == codex_job.id
    assert await repository.find_by_id(codex_job.id) == codex_job


async def test_get_status_codex_job_use_case_returns_stored_job() -> None:
    # Arrange
    repository = FakeCodexJobRepository()
    codex_job = CodexJob.create(CodexJobPrompt("Review repository"))
    await repository.save(codex_job)
    use_case = new_get_status_codex_job_use_case(repository)

    # Act
    found = await use_case.execute(codex_job.id)

    # Assert
    assert found == codex_job


async def test_get_status_codex_job_use_case_raises_when_missing() -> None:
    # Arrange
    use_case = new_get_status_codex_job_use_case(FakeCodexJobRepository())

    # Act / Assert
    with pytest.raises(CodexJobNotFoundError):
        await use_case.execute(CodexJobId.generate())


async def test_abort_codex_job_use_case_aborts_stored_job() -> None:
    # Arrange
    repository = FakeCodexJobRepository()
    starter = FakeCodexJobStarter()
    codex_job = CodexJob.create(CodexJobPrompt("Review repository"))
    codex_job.attach_backend_job("backend-job-id")
    await repository.save(codex_job)
    use_case = new_abort_codex_job_use_case(repository, starter)

    # Act
    aborted = await use_case.execute(codex_job.id)

    # Assert
    assert aborted.status == CodexJobStatus.ABORTED
    assert starter.aborted_backend_job_id == "backend-job-id"


async def test_execute_codex_job_use_case_updates_stored_status() -> None:
    # Arrange
    repository = FakeCodexJobRepository()
    codex_job = CodexJob.create(CodexJobPrompt("Review repository"))
    await repository.save(codex_job)
    use_case = new_execute_codex_job_use_case(repository, FakeCodexJobRunner())

    # Act
    result = await use_case.execute(codex_job.id)

    # Assert
    found = await repository.find_by_id(codex_job.id)
    assert result == "done: Review repository"
    assert found is not None
    assert found.status == CodexJobStatus.SUCCEEDED
    assert found.result == result
