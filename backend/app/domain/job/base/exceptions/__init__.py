"""Expose job domain exceptions."""

from __future__ import annotations

from app.domain.job.base.exceptions.duplicate_job_contract_error import (
    DuplicateJobContractError,
)
from app.domain.job.base.exceptions.job_cancel_access_denied_error import (
    JobCancelAccessDeniedError,
)
from app.domain.job.base.exceptions.job_cancel_error import JobCancelError
from app.domain.job.base.exceptions.job_cancel_not_allowed_error import (
    JobCancelNotAllowedError,
)
from app.domain.job.base.exceptions.job_cancel_not_found_error import (
    JobCancelNotFoundError,
)
from app.domain.job.base.exceptions.job_contract_error import JobContractError
from app.domain.job.base.exceptions.job_create_error import JobCreateError
from app.domain.job.base.exceptions.job_create_not_pending_error import (
    JobCreateNotPendingError,
)
from app.domain.job.base.exceptions.job_delete_error import JobDeleteError
from app.domain.job.base.exceptions.job_delete_not_allowed_error import (
    JobDeleteNotAllowedError,
)
from app.domain.job.base.exceptions.job_has_children_error import JobHasChildrenError
from app.domain.job.base.exceptions.job_serialization_error import JobSerializationError
from app.domain.job.base.exceptions.unknown_job_contract_error import (
    UnknownJobContractError,
)

__all__ = (
    "DuplicateJobContractError",
    "JobCancelAccessDeniedError",
    "JobCancelError",
    "JobCancelNotAllowedError",
    "JobCancelNotFoundError",
    "JobContractError",
    "JobCreateError",
    "JobCreateNotPendingError",
    "JobDeleteError",
    "JobDeleteNotAllowedError",
    "JobHasChildrenError",
    "JobSerializationError",
    "UnknownJobContractError",
)
