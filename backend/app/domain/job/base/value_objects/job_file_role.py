"""Define job file roles."""

from __future__ import annotations

from enum import StrEnum


class JobFileRole(StrEnum):
    """Represent the role of a file in a job context."""

    INPUT = "input"
    OUTPUT = "output"
    PRIMARY_OUTPUT = "primary_output"
    LOG = "log"
