"""Codex HTTP routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from app.domain.job import ActorType, Initiator
from app.domain.job.codex_auth_job_use_case import CodexAuthInputV1, CodexAuthJobV1
from app.domain.job.codex_run_job_use_case import CodexRunInputV1, CodexRunJobV1
from app.domain.user.entities import User
from app.infrastructure.di import (
    get_codex_auth_code_and_url_use_case,
    get_job_launcher,
)
from app.presentation.api.codex import (
    CodexAuthCodePublic,
    CodexRunCreate,
    JobLaunchPublic,
)
from app.presentation.api.common.deps import CurrentUser
from app.usecase.job import (
    CodexAuthCodeAccessDeniedError,
    CodexAuthCodeJobNotFoundError,
    CodexAuthCodeJobTypeError,
    GetCodexAuthCodeAndUrlUseCase,
    JobLauncher,
)

router = APIRouter(prefix="/codex", tags=["codex"])


@router.post("/auth", response_model=JobLaunchPublic)
async def launch_codex_auth(
    current_user: CurrentUser,
    launcher: Annotated[JobLauncher, Depends(get_job_launcher)],
) -> JobLaunchPublic:
    """Queue a Codex device auth job."""
    job = CodexAuthJobV1.new(
        initiator=_initiator_from_user(current_user),
        input=CodexAuthInputV1(),
        name="Codex auth",
        description="Authenticate Codex through device login",
    )
    job_id = await launcher.launch(job)
    return JobLaunchPublic(job_id=job_id)


@router.get(
    "/auth/get_code_and_url/{job_id}",
    response_model=CodexAuthCodePublic,
    responses={204: {"description": "Codex auth code is not ready yet"}},
)
async def get_codex_auth_code_and_url(
    current_user: CurrentUser,
    use_case: Annotated[
        GetCodexAuthCodeAndUrlUseCase,
        Depends(get_codex_auth_code_and_url_use_case),
    ],
    job_id: UUID,
) -> CodexAuthCodePublic | Response:
    """Return Codex device auth URL and code once the auth job has produced them."""
    try:
        auth_code = await use_case.execute(
            job_id=job_id,
            current_user_id=str(current_user.id),
        )
    except CodexAuthCodeJobNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")
    except CodexAuthCodeJobTypeError:
        raise HTTPException(status_code=400, detail="Job is not a Codex auth job")
    except CodexAuthCodeAccessDeniedError:
        raise HTTPException(status_code=403, detail="Job access denied")
    if auth_code is None:
        return Response(status_code=204)
    return CodexAuthCodePublic(
        verification_url=auth_code.verification_url,
        device_code=auth_code.device_code,
    )


@router.post("/run", response_model=JobLaunchPublic)
async def launch_codex_run(
    current_user: CurrentUser,
    launcher: Annotated[JobLauncher, Depends(get_job_launcher)],
    body: CodexRunCreate,
) -> JobLaunchPublic:
    """Queue a Codex run job."""
    job = CodexRunJobV1.new(
        initiator=_initiator_from_user(current_user),
        input=CodexRunInputV1(prompt=body.prompt, workdir=body.workdir),
        name="Codex run",
        description="Run Codex against a workspace",
    )
    job_id = await launcher.launch(job)
    return JobLaunchPublic(job_id=job_id)


def _initiator_from_user(user: User) -> Initiator:
    """Build the root job initiator from the authenticated user."""
    return Initiator(
        type=ActorType.USER,
        external_id=str(user.id),
        display_name=user.email.value,
    )
