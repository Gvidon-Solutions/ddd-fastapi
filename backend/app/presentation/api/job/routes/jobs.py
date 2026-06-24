"""Job HTTP routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.domain.job import JobRepository
from app.infrastructure.di import get_cancel_job_use_case, get_job_repository
from app.presentation.api.common.deps import CurrentUser
from app.presentation.api.job import JobCancelPublic
from app.usecase.job import CancelJobUseCase

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/{job_id}/cancel", response_model=JobCancelPublic)
async def cancel_job(
    current_user: CurrentUser,
    use_case: Annotated[CancelJobUseCase, Depends(get_cancel_job_use_case)],
    jobs: Annotated[JobRepository, Depends(get_job_repository)],
    job_id: UUID,
) -> JobCancelPublic:
    """Cancel a queued or running job."""
    try:
        job = await jobs.get(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.root_initiator.id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Job access denied")

    cancelled = await use_case.execute(job_id)
    if not cancelled:
        raise HTTPException(status_code=409, detail="Job was not cancelled")
    return JobCancelPublic(job_id=job_id, cancelled=True)
