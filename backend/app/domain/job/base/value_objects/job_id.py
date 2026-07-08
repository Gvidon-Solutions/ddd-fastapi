"""Define the Job identifier type."""

from typing import NewType
from uuid import UUID, uuid4

JobId = NewType("JobId", UUID)


def new_job_id() -> JobId:
    """Generate a new identifier for a job."""
    return JobId(uuid4())
