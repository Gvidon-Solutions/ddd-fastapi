"""Codex auth job event 2."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.job.base.entities import JobEvent
from app.domain.job.base.value_objects import JobEventType


@dataclass
class Event2WaitingForUserLoginData:
    """Represent event 2 data."""

    stage: str = "codex_auth"
    status: str = "waiting_for_user"
    verification_url: str | None = None
    user_code: str | None = None
    device_code: str | None = None

    def __getitem__(self, key: str):
        """Return a field value by key."""
        return asdict(self)[key]


@dataclass(kw_only=True)
class Event2WaitingForUserLogin(JobEvent):
    """Represent the event emitted while waiting for Codex device login."""

    id: UUID = field(default_factory=uuid4, init=False)
    type: JobEventType = field(default=JobEventType.STAGE_CHANGED, init=False)
    data: Event2WaitingForUserLoginData = field(
        default_factory=Event2WaitingForUserLoginData,
    )
    message: str | None = field(
        default="Open verification URL and enter user code",
        init=False,
    )
