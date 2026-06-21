"""Codex device login session domain tests."""

from uuid import uuid4

from app.domain.codex_auth.entities import CodexDeviceLoginSession
from app.domain.codex_auth.value_objects import CodexDeviceLoginStatus


def test_codex_device_login_session_stores_authentication_data() -> None:
    # Arrange
    session_id = uuid4()

    # Act
    session = CodexDeviceLoginSession(
        id=session_id,
        status=CodexDeviceLoginStatus.PENDING,
        verification_url="https://auth.openai.com/device",
        user_code="ABCD-EFGH",
        raw_output="Open URL and enter code",
    )

    # Assert
    assert session.id == session_id
    assert session.status == CodexDeviceLoginStatus.PENDING
    assert session.verification_url == "https://auth.openai.com/device"
    assert session.user_code == "ABCD-EFGH"
    assert session.raw_output == "Open URL and enter code"
