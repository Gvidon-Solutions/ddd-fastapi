"""Email utility tests."""

from app.infrastructure.email import generate_reset_password_email, generate_test_email


def test_generate_test_email_renders_subject() -> None:
    # Act
    email = generate_test_email("to@example.com")

    # Assert
    assert "Test email" in email.subject


def test_generate_test_email_renders_html_content() -> None:
    # Act
    email = generate_test_email("to@example.com")

    # Assert
    assert email.html_content


def test_generate_reset_password_email_renders_subject() -> None:
    # Act
    email = generate_reset_password_email(
        "to@example.com",
        "user@example.com",
        "token",
    )

    # Assert
    assert "Password recovery" in email.subject


def test_generate_reset_password_email_renders_html_content() -> None:
    # Act
    email = generate_reset_password_email(
        "to@example.com",
        "user@example.com",
        "token",
    )

    # Assert
    assert email.html_content
