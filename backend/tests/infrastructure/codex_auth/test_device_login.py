"""Codex device login infrastructure tests."""

from app.infrastructure.codex_auth import parse_device_login_output


def test_parse_device_login_output_extracts_url_and_code() -> None:
    # Arrange
    output = (
        "Open https://auth.openai.com/device in your browser\nEnter code: ABCD-EFGH\n"
    )

    # Act
    parsed = parse_device_login_output(output)

    # Assert
    assert parsed == {
        "verification_url": "https://auth.openai.com/device",
        "user_code": "ABCD-EFGH",
    }
