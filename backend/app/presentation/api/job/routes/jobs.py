"""Job HTTP routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.domain.job import (
    JobCancelAccessDeniedError,
    JobCancelNotAllowedError,
    JobCancelNotFoundError,
    JobReadAccessDeniedError,
    JobReadNotFoundError,
)
from app.infrastructure.di import (
    get_cancel_job_use_case,
    get_job_details_use_case,
    get_list_jobs_use_case,
)
from app.presentation.api.common.deps import CurrentUser
from app.presentation.api.job import (
    JobCancelPublic,
    JobDetailsPublic,
    JobsPublic,
    JobSummaryPublic,
)
from app.usecase.job import CancelJobUseCase, GetJobDetailsUseCase, ListJobsUseCase

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=JobsPublic)
async def list_jobs(
    current_user: CurrentUser,
    use_case: ListJobsUseCase = Depends(get_list_jobs_use_case),
) -> JobsPublic:
    """Return jobs created by the current user."""
    jobs = await use_case.execute(current_user_id=str(current_user.id))
    return JobsPublic(
        data=[JobSummaryPublic.from_value_object(job) for job in jobs],
        count=len(jobs),
    )


@router.get("/{job_id}", response_model=JobDetailsPublic)
async def get_job_details(
    current_user: CurrentUser,
    job_id: UUID,
    use_case: GetJobDetailsUseCase = Depends(get_job_details_use_case),
) -> JobDetailsPublic:
    """Return one job created by the current user."""
    try:
        details = await use_case.execute(job_id, current_user_id=str(current_user.id))
    except JobReadNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")
    except JobReadAccessDeniedError:
        raise HTTPException(status_code=403, detail="Job access denied")
    return JobDetailsPublic.from_details(details)


@router.post("/{job_id}/cancel", response_model=JobCancelPublic)
async def cancel_job(
    current_user: CurrentUser,
    job_id: UUID,
    use_case: CancelJobUseCase = Depends(get_cancel_job_use_case),
) -> JobCancelPublic:
    """Cancel a queued or running job."""
    try:
        await use_case.execute(job_id, current_user_id=str(current_user.id))
    except JobCancelNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")
    except JobCancelAccessDeniedError:
        raise HTTPException(status_code=403, detail="Job access denied")
    except JobCancelNotAllowedError:
        raise HTTPException(status_code=409, detail="Job was not cancelled")
    return JobCancelPublic(job_id=job_id, cancelled=True)
