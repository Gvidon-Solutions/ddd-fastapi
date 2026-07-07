"""Job serialization error."""

from __future__ import annotations

from app.domain.job.base.exceptions.job_contract_error import JobContractError


class JobSerializationError(JobContractError):
    """Raised when persisted job data cannot be decoded."""

    detail = "Job payload cannot be serialized or deserialized."
