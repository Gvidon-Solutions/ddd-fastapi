"""Expose the generic job domain."""

from __future__ import annotations

from .entities import AnyJob, File, Job, JobEvent, JobEventPayload, JobFile
from .exceptions import (
    DuplicateJobContractError,
    JobDeleteError,
    JobDeleteNotAllowedError,
    JobHasChildrenError,
    JobSerializationError,
    UnknownJobContractError,
)
from .job_contract import JobContract
from .job_registry import JobRegistry, job_registry
from .repositories import (
    FileRepository,
    JobDetailProjection,
    JobEventRepository,
    JobExecutionRecord,
    JobFileRepository,
    JobQueryRepository,
    JobRepository,
    JobSummary,
)
from .serialization import deserialize_json, serialize_json
from .value_objects import (
    ActorType,
    FileKind,
    FileLocation,
    FileLocationType,
    FileStatus,
    Initiator,
    JobError,
    JobFileRole,
    JobStatus,
)

__all__ = (
    "AnyJob",
    "ActorType",
    "DuplicateJobContractError",
    "JobDeleteError",
    "JobDeleteNotAllowedError",
    "JobHasChildrenError",
    "File",
    "FileKind",
    "FileLocation",
    "FileLocationType",
    "FileRepository",
    "FileStatus",
    "Initiator",
    "Job",
    "JobContract",
    "JobError",
    "JobEvent",
    "JobEventPayload",
    "JobEventRepository",
    "JobDetailProjection",
    "JobExecutionRecord",
    "JobFile",
    "JobFileRepository",
    "JobFileRole",
    "JobQueryRepository",
    "JobRepository",
    "JobSummary",
    "JobRegistry",
    "JobSerializationError",
    "JobStatus",
    "UnknownJobContractError",
    "deserialize_json",
    "job_registry",
    "serialize_json",
)
