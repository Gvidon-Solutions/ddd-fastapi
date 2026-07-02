"""Define file statuses."""

from __future__ import annotations

from enum import StrEnum


class FileStatus(StrEnum):
    """Represent file lifecycle status."""

    ACTIVE = "active"
    PENDING_DELETE = "pending_delete"
