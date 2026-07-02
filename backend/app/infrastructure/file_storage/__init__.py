"""Filesystem-backed file storage adapters."""

from __future__ import annotations

from .filesystem_file_storage import FilesystemFileStorage, new_filesystem_file_storage

__all__ = ("FilesystemFileStorage", "new_filesystem_file_storage")
