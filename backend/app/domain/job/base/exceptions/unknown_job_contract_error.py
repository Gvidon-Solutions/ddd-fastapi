"""Unknown job contract error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_contract_error import JobContractError


class UnknownJobContractError(JobContractError):
    """Raised when a persisted job contract is unknown to this code."""

    detail = "Unknown job contract."
