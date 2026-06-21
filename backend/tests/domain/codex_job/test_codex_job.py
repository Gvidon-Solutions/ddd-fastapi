"""CodexJob entity tests."""

from app.domain.codex_job.entities import CodexJob
from app.domain.codex_job.value_objects import CodexJobPrompt, CodexJobStatus


def test_codex_job_create_starts_queued() -> None:
    # Arrange
    prompt = CodexJobPrompt("Review repository")

    # Act
    codex_job = CodexJob.create(prompt)

    # Assert
    assert codex_job.prompt == prompt
    assert codex_job.status == CodexJobStatus.QUEUED
    assert codex_job.backend_job_id is None


def test_codex_job_status_transitions() -> None:
    # Arrange
    codex_job = CodexJob.create(CodexJobPrompt("Review repository"))

    # Act
    codex_job.attach_backend_job("backend-job-id")
    codex_job.start()
    codex_job.complete("done")

    # Assert
    assert codex_job.backend_job_id == "backend-job-id"
    assert codex_job.status == CodexJobStatus.SUCCEEDED
    assert codex_job.result == "done"
    assert codex_job.started_at is not None
    assert codex_job.finished_at is not None
