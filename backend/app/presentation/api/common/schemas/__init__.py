"""Common API schemas."""

from __future__ import annotations

from .message import Message
from .new_password import NewPassword
from .token import Token
from .token_payload import TokenPayload

__all__ = ("Message", "NewPassword", "Token", "TokenPayload")
