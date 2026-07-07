"""Define job event payload base entity."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.job.base.value_objects.job_id import JobId


@dataclass(kw_only=True)
class JobEventPayload:
    """Represent the job-specific payload for an emitted event."""

    job_id: JobId
