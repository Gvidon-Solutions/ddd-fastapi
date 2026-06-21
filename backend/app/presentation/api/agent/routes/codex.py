"""Codex runtime HTTP routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.domain.codex_auth.entities import CodexDeviceLoginSession
from app.domain.user.entities import User
from app.infrastructure.di import (
    get_cancel_codex_device_login_use_case,
    get_codex_login_status_use_case,
    get_find_codex_device_login_use_case,
    get_start_codex_device_login_use_case,
)
from app.presentation.api.agent.schemas import CodexDeviceLogin, CodexLoginStatus
from app.presentation.api.common.deps import get_current_active_superuser
from app.usecase.codex_auth import (
    CancelCodexDeviceLoginUseCase,
    FindCodexDeviceLoginUseCase,
    GetCodexLoginStatusUseCase,
    StartCodexDeviceLoginUseCase,
)

router = APIRouter(prefix="/agents/codex", tags=["agents"])

SuperuserDep = Annotated[User, Depends(get_current_active_superuser)]


def _device_login_response(session: CodexDeviceLoginSession) -> CodexDeviceLogin:
    """Convert a Codex device-login session to its API response."""
    return CodexDeviceLogin(
        session_id=session.id,
        status=session.status.value,
        verification_url=session.verification_url,
        user_code=session.user_code,
        raw_output=session.raw_output,
        return_code=session.return_code,
    )


@router.get("/login/status", response_model=CodexLoginStatus)
async def codex_login_status(
    _current_user: SuperuserDep,
    use_case: Annotated[
        GetCodexLoginStatusUseCase,
        Depends(get_codex_login_status_use_case),
    ],
) -> CodexLoginStatus:
    """Return whether the Codex CLI is authenticated."""
    status = await use_case.execute()
    return CodexLoginStatus(
        authenticated=status.authenticated,
        raw_output=status.raw_output,
    )


@router.post("/login/device", response_model=CodexDeviceLogin)
async def start_codex_device_login(
    _current_user: SuperuserDep,
    use_case: Annotated[
        StartCodexDeviceLoginUseCase,
        Depends(get_start_codex_device_login_use_case),
    ],
) -> CodexDeviceLogin:
    """Start Codex CLI device-code authentication."""
    session = await use_case.execute()
    return _device_login_response(session)


@router.get("/login/device/{session_id}", response_model=CodexDeviceLogin)
async def read_codex_device_login(
    _current_user: SuperuserDep,
    use_case: Annotated[
        FindCodexDeviceLoginUseCase,
        Depends(get_find_codex_device_login_use_case),
    ],
    session_id: UUID,
) -> CodexDeviceLogin:
    """Return a Codex device-code authentication session."""
    session = await use_case.execute(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Codex login session not found")
    return _device_login_response(session)


@router.delete("/login/device/{session_id}", response_model=CodexDeviceLogin)
async def cancel_codex_device_login(
    _current_user: SuperuserDep,
    use_case: Annotated[
        CancelCodexDeviceLoginUseCase,
        Depends(get_cancel_codex_device_login_use_case),
    ],
    session_id: UUID,
) -> CodexDeviceLogin:
    """Cancel a running Codex device-code authentication session."""
    session = await use_case.execute(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Codex login session not found")
    return _device_login_response(session)
