"""Expose the generic job domain."""

from __future__ import annotations

from .entities import AnyJob, Job, JobContract, JobEvent, JobFile
from .exceptions import (
    DuplicateJobContractError,
    JobCancelAccessDeniedError,
    JobCancelError,
    JobCancelNotAllowedError,
    JobCancelNotFoundError,
    JobCreateError,
    JobCreateNotPendingError,
    JobDeleteError,
    JobDeleteNotAllowedError,
    JobHasChildrenError,
    JobReadAccessDeniedError,
    JobReadError,
    JobReadNotFoundError,
    JobSerializationError,
    UnknownJobContractError,
)
from .job_registry import JobTypeRegistry, get_job_class, get_job_type_registry
from .repositories import (
    JobExecutionRecord,
    JobRepository,
)
from .value_objects import (
    ActorType,
    Initiator,
    JobError,
    JobEventPayload,
    JobFileRole,
    JobStatus,
)
from .value_objects.job_details import JobDetails
from .value_objects.job_summary import JobSummary

__all__ = (
    "AnyJob",
    "ActorType",
    "DuplicateJobContractError",
    "JobCancelAccessDeniedError",
    "JobCancelError",
    "JobCancelNotAllowedError",
    "JobCancelNotFoundError",
    "JobCreateError",
    "JobCreateNotPendingError",
    "JobDeleteError",
    "JobDeleteNotAllowedError",
    "JobHasChildrenError",
    "JobReadAccessDeniedError",
    "JobReadError",
    "JobReadNotFoundError",
    "Initiator",
    "Job",
    "JobContract",
    "JobError",
    "JobEvent",
    "JobEventPayload",
    "JobDetails",
    "JobExecutionRecord",
    "JobFile",
    "JobFileRole",
    "JobRepository",
    "JobSummary",
    "JobTypeRegistry",
    "JobSerializationError",
    "JobStatus",
    "UnknownJobContractError",
    "get_job_class",
    "get_job_type_registry",
)
