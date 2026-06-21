"""CodexJobDTO tests."""

from app.domain.codex_job.entities import CodexJob
from app.domain.codex_job.value_objects import CodexJobPrompt, CodexJobStatus
from app.infrastructure.sqlmodel.codex_job import CodexJobDTO


def test_codex_job_dto_uses_codex_job_table_name() -> None:
    # Act
    table_name = CodexJobDTO.__tablename__

    # Assert
    assert table_name == "codex_job"


def test_codex_job_dto_round_trips_entity_fields() -> None:
    # Arrange
    codex_job = CodexJob.create(CodexJobPrompt("Review repository"))
    codex_job.attach_backend_job("backend-job-id")
    codex_job.start()
    codex_job.complete("done")

    # Act
    entity = CodexJobDTO.from_entity(codex_job).to_entity()

    # Assert
    assert entity == codex_job
    assert entity.prompt == codex_job.prompt
    assert entity.status == CodexJobStatus.SUCCEEDED
    assert entity.backend_job_id == "backend-job-id"
    assert entity.result == "done"
