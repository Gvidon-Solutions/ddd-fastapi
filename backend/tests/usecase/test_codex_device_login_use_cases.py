"""Codex device login use case tests."""

from uuid import UUID, uuid4

import pytest

from app.domain.codex_auth.entities import CodexDeviceLoginSession, CodexLoginStatus
from app.domain.codex_auth.value_objects import CodexDeviceLoginStatus
from app.usecase.codex_auth import (
    new_cancel_codex_device_login_use_case,
    new_find_codex_device_login_use_case,
    new_get_codex_login_status_use_case,
    new_start_codex_device_login_use_case,
)

pytestmark = pytest.mark.anyio


class FakeCodexDeviceLoginGateway:
    """Fake Codex device login gateway."""

    def __init__(self) -> None:
        """Initialize fake state."""
        self.session = CodexDeviceLoginSession(
            id=uuid4(),
            status=CodexDeviceLoginStatus.PENDING,
            verification_url="https://auth.openai.com/device",
            user_code="ABCD-EFGH",
        )

    async def status(self) -> CodexLoginStatus:
        """Return fake login status."""
        return CodexLoginStatus(authenticated=True, raw_output="Logged in")

    async def start(self) -> CodexDeviceLoginSession:
        """Return fake started session."""
        return self.session

    async def find_by_id(self, session_id: UUID) -> CodexDeviceLoginSession | None:
        """Find fake session."""
        return self.session if session_id == self.session.id else None

    async def cancel(self, session_id: UUID) -> CodexDeviceLoginSession | None:
        """Cancel fake session."""
        if session_id != self.session.id:
            return None
        return CodexDeviceLoginSession(
            id=self.session.id,
            status=CodexDeviceLoginStatus.FAILED,
            return_code=-15,
        )


async def test_get_codex_login_status_use_case_returns_status() -> None:
    # Arrange
    gateway = FakeCodexDeviceLoginGateway()
    use_case = new_get_codex_login_status_use_case(gateway)

    # Act
    status = await use_case.execute()

    # Assert
    assert status.authenticated is True
    assert status.raw_output == "Logged in"


async def test_start_codex_device_login_use_case_starts_session() -> None:
    # Arrange
    gateway = FakeCodexDeviceLoginGateway()
    use_case = new_start_codex_device_login_use_case(gateway)

    # Act
    session = await use_case.execute()

    # Assert
    assert session == gateway.session


async def test_find_codex_device_login_use_case_finds_session() -> None:
    # Arrange
    gateway = FakeCodexDeviceLoginGateway()
    use_case = new_find_codex_device_login_use_case(gateway)

    # Act
    session = await use_case.execute(gateway.session.id)

    # Assert
    assert session == gateway.session


async def test_cancel_codex_device_login_use_case_cancels_session() -> None:
    # Arrange
    gateway = FakeCodexDeviceLoginGateway()
    use_case = new_cancel_codex_device_login_use_case(gateway)

    # Act
    session = await use_case.execute(gateway.session.id)

    # Assert
    assert session is not None
    assert session.status == CodexDeviceLoginStatus.FAILED
    assert session.return_code == -15
