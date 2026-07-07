"""Define job event payload base entity."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(kw_only=True)
class JobEventPayload:
    """Represent the job-specific payload for an emitted event."""

    job_id: UUID
