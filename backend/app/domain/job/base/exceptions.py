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
