"""Codex device-auth login data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodexDeviceAuth:
    """Represent Codex device-auth login data."""

    verification_url: str | None = None
    device_code: str | None = None
