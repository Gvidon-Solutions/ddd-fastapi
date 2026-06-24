"""Expose the generic job domain."""

from __future__ import annotations

from .entities import Job, JobArtifact, JobEvent, JobEventPayload
from .repositories import JobArtifactRepository, JobEventRepository, JobRepository
from .value_objects import (
    Actor,
    ActorType,
    ArtifactKind,
    ArtifactLocation,
    ArtifactLocationType,
    ArtifactRole,
    JobError,
    JobEventType,
    JobStage,
    JobStatus,
)

__all__ = (
    "Actor",
    "ActorType",
    "ArtifactKind",
    "ArtifactLocation",
    "ArtifactLocationType",
    "ArtifactRole",
    "Job",
    "JobArtifact",
    "JobArtifactRepository",
    "JobError",
    "JobEvent",
    "JobEventPayload",
    "JobEventRepository",
    "JobEventType",
    "JobRepository",
    "JobStage",
    "JobStatus",
)
