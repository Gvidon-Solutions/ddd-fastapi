"""Security and email infrastructure tests."""

from datetime import timedelta

from app.infrastructure.email import generate_reset_password_email, generate_test_email
from app.infrastructure.security import (
    create_access_token,
    generate_password_reset_token,
    new_password_hasher,
    verify_password_reset_token,
)


def test_password_hasher_hashes_and_verifies_password() -> None:
    hasher = new_password_hasher()
    hashed = hasher.hash_password("secret")

    assert hashed.value != "secret"
    assert hasher.verify_password("secret", hashed).verified
    assert not hasher.verify_password("wrong", hashed).verified


def test_access_and_password_reset_tokens_round_trip() -> None:
    access_token = create_access_token("subject", timedelta(minutes=1))
    reset_token = generate_password_reset_token("user@example.com")

    assert access_token
    assert verify_password_reset_token(reset_token) == "user@example.com"
    assert verify_password_reset_token("invalid") is None


def test_email_factories_render_subjects() -> None:
    test_email = generate_test_email("to@example.com")
    reset_email = generate_reset_password_email(
        "to@example.com",
        "user@example.com",
        "token",
    )

    assert "Test email" in test_email.subject
    assert "Password recovery" in reset_email.subject
    assert test_email.html_content
    assert reset_email.html_content
