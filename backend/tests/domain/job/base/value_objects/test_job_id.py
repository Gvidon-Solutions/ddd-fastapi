"""JobId value object tests."""

from uuid import UUID

from app.domain.job import new_job_id


def test_job_id_generates_uuid() -> None:
    # Act
    job_id = new_job_id()

    # Assert
    assert isinstance(job_id, UUID)
    assert str(job_id) == str(job_id)
