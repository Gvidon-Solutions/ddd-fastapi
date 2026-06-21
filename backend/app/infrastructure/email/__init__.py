"""Email infrastructure services."""

from __future__ import annotations

from .utils import (
    EmailData,
    generate_new_account_email,
    generate_reset_password_email,
    generate_test_email,
    send_email,
)

__all__ = (
    "EmailData",
    "generate_new_account_email",
    "generate_reset_password_email",
    "generate_test_email",
    "send_email",
)
