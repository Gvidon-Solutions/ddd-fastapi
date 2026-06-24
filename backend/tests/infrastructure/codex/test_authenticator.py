"""Codex authenticator tests."""

from app.infrastructure.codex.authenticator import parse_device_login_output


def test_parse_device_login_output_extracts_url_and_device_code() -> None:
    # Act
    parsed = parse_device_login_output(
        "Open https://auth.openai.com/device and enter code ABCD-EFGH"
    )

    # Assert
    assert parsed == {
        "verification_url": "https://auth.openai.com/device",
        "device_code": "ABCD-EFGH",
    }
