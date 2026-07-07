"""JobId value object tests."""

from uuid import UUID

from app.domain.job import JobId


def test_job_id_generates_uuid() -> None:
    # Act
    job_id = JobId.generate()

    # Assert
    assert isinstance(job_id.value, UUID)
    assert str(job_id) == str(job_id.value)
