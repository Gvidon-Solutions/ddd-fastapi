"""Job domain exceptions."""

from __future__ import annotations


class JobContractError(Exception):
    """Base class for job contract errors."""


class DuplicateJobContractError(JobContractError):
    """Raised when a job contract is registered twice."""


class UnknownJobContractError(JobContractError):
    """Raised when a persisted job contract is unknown to this code."""


class JobSerializationError(JobContractError):
    """Raised when persisted job data cannot be decoded."""


class JobDeleteError(Exception):
    """Base class for job deletion errors."""


class JobDeleteNotAllowedError(JobDeleteError):
    """Raised when a non-terminal job is deleted."""


class JobHasChildrenError(JobDeleteError):
    """Raised when a job has children and cascade deletion is disabled."""
