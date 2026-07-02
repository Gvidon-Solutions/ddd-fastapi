"""Expose the generic job domain."""

from __future__ import annotations

from .entities import AnyJob, Job, JobArtifact, JobEvent, JobEventPayload
from .exceptions import (
    DuplicateJobContractError,
    JobSerializationError,
    UnknownJobContractError,
)
from .job_contract import JobContract
from .job_registry import JobRegistry, job_registry
from .repositories import (
    JobArtifactRepository,
    JobEventRepository,
    JobExecutionRecord,
    JobRepository,
)
from .serialization import deserialize_json, serialize_json
from .value_objects import (
    Actor,
    ActorType,
    ArtifactKind,
    ArtifactLocation,
    ArtifactLocationType,
    ArtifactRole,
    Initiator,
    JobError,
    JobEventType,
    JobStage,
    JobStatus,
)

__all__ = (
    "AnyJob",
    "Actor",
    "ActorType",
    "DuplicateJobContractError",
    "ArtifactKind",
    "ArtifactLocation",
    "ArtifactLocationType",
    "ArtifactRole",
    "Initiator",
    "Job",
    "JobArtifact",
    "JobArtifactRepository",
    "JobContract",
    "JobError",
    "JobEvent",
    "JobEventPayload",
    "JobEventRepository",
    "JobEventType",
    "JobExecutionRecord",
    "JobRepository",
    "JobRegistry",
    "JobSerializationError",
    "JobStage",
    "JobStatus",
    "UnknownJobContractError",
    "deserialize_json",
    "job_registry",
    "serialize_json",
)
