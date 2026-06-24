"""Define artifact roles."""

from __future__ import annotations

from enum import StrEnum


class ArtifactRole(StrEnum):
    """Represent the role an artifact plays in a job execution."""

    OUTPUT = "output"
    LOG = "log"
    INTERMEDIATE = "intermediate"
    DEBUG = "debug"
