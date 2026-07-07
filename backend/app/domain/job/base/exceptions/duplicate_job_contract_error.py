"""Duplicate job contract error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_contract_error import JobContractError


class DuplicateJobContractError(JobContractError):
    """Raised when a job contract is registered twice."""

    detail = "Job contract already exists."
