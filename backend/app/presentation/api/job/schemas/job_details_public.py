"""Job details response schema."""

from typing import Any

from fastapi.encoders import jsonable_encoder

from app.domain.job import JobDetails
from app.presentation.api.job.schemas.job_error_public import JobErrorPublic
from app.presentation.api.job.schemas.job_event_public import JobEventPublic
from app.presentation.api.job.schemas.job_file_public import JobFilePublic
from app.presentation.api.job.schemas.job_summary_public import JobSummaryPublic


class JobDetailsPublic(JobSummaryPublic):
    """Job details response schema."""

    input: dict[str, Any]
    result: dict[str, Any] | None
    error: JobErrorPublic | None
    files: list[JobFilePublic]
    events: list[JobEventPublic]

    @staticmethod
    def from_details(details: JobDetails) -> "JobDetailsPublic":
        """Build an API response from a domain value object."""
        summary = JobSummaryPublic.from_value_object(details)
        return JobDetailsPublic(
            id=summary.id,
            type=summary.type,
            version=summary.version,
            name=summary.name,
            status=summary.status,
            initiator=summary.initiator,
            parent_job_id=summary.parent_job_id,
            requested_at=summary.requested_at,
            updated_at=summary.updated_at,
            started_at=summary.started_at,
            finished_at=summary.finished_at,
            input=jsonable_encoder(details.input),
            result=jsonable_encoder(details.result)
            if details.result is not None
            else None,
            error=JobErrorPublic.from_value_object(details.error)
            if details.error is not None
            else None,
            files=[JobFilePublic.from_entity(file) for file in details.files],
            events=[JobEventPublic.from_entity(event) for event in details.events],
        )
