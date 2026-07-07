"""Job HTTP routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.domain.job import (
    JobCancelAccessDeniedError,
    JobCancelNotAllowedError,
    JobCancelNotFoundError,
)
from app.infrastructure.di import get_cancel_job_use_case
from app.presentation.api.common.deps import CurrentUser
from app.presentation.api.job import JobCancelPublic
from app.usecase.job import CancelJobUseCase

router = APIRouter(prefix="/jobs", tags=["jobs"])


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
