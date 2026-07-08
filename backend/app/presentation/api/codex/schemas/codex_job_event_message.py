"""Codex realtime job event message specs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

import msgspec


class CodexAuthStartedPayload(msgspec.Struct, kw_only=True):
    """Codex auth started payload."""

    job_id: str
    stage: str


class CodexAuthUserLoginRequestedPayload(msgspec.Struct, kw_only=True):
    """Codex auth user-login-requested payload."""

    job_id: str
    stage: str
    status: str


class CodexAuthResultPayload(msgspec.Struct, kw_only=True):
    """Codex auth result payload."""

    authenticated: bool
    error_message: str | None = None


class CodexAuthSucceededPayload(msgspec.Struct, kw_only=True):
    """Codex auth succeeded payload."""

    job_id: str
    summary: CodexAuthResultPayload


class CodexAuthFailedPayload(msgspec.Struct, kw_only=True):
    """Codex auth failed payload."""

    job_id: str
    error: str


class CodexAuthCancelledPayload(msgspec.Struct, kw_only=True):
    """Codex auth cancelled payload."""

    job_id: str
    reason: str


class CodexRunStartedPayload(msgspec.Struct, kw_only=True):
    """Codex run started payload."""

    job_id: str
    stage: str
    workdir: str


class CodexRunFileCreatedPayload(msgspec.Struct, kw_only=True):
    """Codex run file-created payload."""

    job_id: str
    file_id: str
    filename: str


class CodexRunSucceededPayload(msgspec.Struct, kw_only=True):
    """Codex run succeeded payload."""

    job_id: str
    output_file_id: str | None
    log_files: int
    generated_files: int


class CodexRunFailedPayload(msgspec.Struct, kw_only=True):
    """Codex run failed payload."""

    job_id: str
    error: str


class CodexRunCancelledPayload(msgspec.Struct, kw_only=True):
    """Codex run cancelled payload."""

    job_id: str
    reason: str


class CodexExecOutputPayload(msgspec.Struct, kw_only=True):
    """Codex exec output payload."""

    job_id: str
    channel: Literal["stdout", "stderr"]
    line_number: int
    line: str


class CodexEventBase(msgspec.Struct, kw_only=True):
    """Base Codex event envelope."""

    event_id: str
    source: str
    version: Literal["v1"]
    created_at: str


class CodexAuthStartedEvent(CodexEventBase, kw_only=True):
    """Codex auth started event."""

    type: Literal["CodexAuthStartedV1"]
    payload: CodexAuthStartedPayload


class CodexAuthUserLoginRequestedEvent(CodexEventBase, kw_only=True):
    """Codex auth user-login-requested event."""

    type: Literal["CodexAuthUserLoginRequestedV1"]
    payload: CodexAuthUserLoginRequestedPayload


class CodexAuthSucceededEvent(CodexEventBase, kw_only=True):
    """Codex auth succeeded event."""

    type: Literal["CodexAuthSucceededV1"]
    payload: CodexAuthSucceededPayload


class CodexAuthFailedEvent(CodexEventBase, kw_only=True):
    """Codex auth failed event."""

    type: Literal["CodexAuthFailedV1"]
    payload: CodexAuthFailedPayload


class CodexAuthCancelledEvent(CodexEventBase, kw_only=True):
    """Codex auth cancelled event."""

    type: Literal["CodexAuthCancelledV1"]
    payload: CodexAuthCancelledPayload


class CodexRunStartedEvent(CodexEventBase, kw_only=True):
    """Codex run started event."""

    type: Literal["CodexRunStartedV1"]
    payload: CodexRunStartedPayload


class CodexRunFileCreatedEvent(CodexEventBase, kw_only=True):
    """Codex run file-created event."""

    type: Literal["CodexRunFileCreatedV1"]
    payload: CodexRunFileCreatedPayload


class CodexRunSucceededEvent(CodexEventBase, kw_only=True):
    """Codex run succeeded event."""

    type: Literal["CodexRunSucceededV1"]
    payload: CodexRunSucceededPayload


class CodexRunFailedEvent(CodexEventBase, kw_only=True):
    """Codex run failed event."""

    type: Literal["CodexRunFailedV1"]
    payload: CodexRunFailedPayload


class CodexRunCancelledEvent(CodexEventBase, kw_only=True):
    """Codex run cancelled event."""

    type: Literal["CodexRunCancelledV1"]
    payload: CodexRunCancelledPayload


class CodexExecOutputEvent(CodexEventBase, kw_only=True):
    """Codex exec output event."""

    type: Literal["CodexExecOutputV1"]
    payload: CodexExecOutputPayload


CodexJobEvent = (
    CodexAuthStartedEvent
    | CodexAuthUserLoginRequestedEvent
    | CodexAuthSucceededEvent
    | CodexAuthFailedEvent
    | CodexAuthCancelledEvent
    | CodexRunStartedEvent
    | CodexRunFileCreatedEvent
    | CodexRunSucceededEvent
    | CodexRunFailedEvent
    | CodexRunCancelledEvent
    | CodexExecOutputEvent
)


class CodexJobEventMessage(msgspec.Struct, kw_only=True):
    """Codex realtime event stream message."""

    stream_id: str
    event: CodexJobEvent


_CODEX_EVENT_TYPES: dict[str, type[CodexJobEvent]] = {
    "CodexAuthStartedV1": CodexAuthStartedEvent,
    "CodexAuthUserLoginRequestedV1": CodexAuthUserLoginRequestedEvent,
    "CodexAuthSucceededV1": CodexAuthSucceededEvent,
    "CodexAuthFailedV1": CodexAuthFailedEvent,
    "CodexAuthCancelledV1": CodexAuthCancelledEvent,
    "CodexRunStartedV1": CodexRunStartedEvent,
    "CodexRunFileCreatedV1": CodexRunFileCreatedEvent,
    "CodexRunSucceededV1": CodexRunSucceededEvent,
    "CodexRunFailedV1": CodexRunFailedEvent,
    "CodexRunCancelledV1": CodexRunCancelledEvent,
    "CodexExecOutputV1": CodexExecOutputEvent,
}


def to_codex_job_event_message(
    *,
    stream_id: str,
    event: Mapping[str, object],
) -> CodexJobEventMessage | None:
    """Return a typed Codex realtime message for known Codex event records."""
    event_type = event.get("type")
    if not isinstance(event_type, str):
        return None
    event_class = _CODEX_EVENT_TYPES.get(event_type)
    if event_class is None:
        return None
    return CodexJobEventMessage(
        stream_id=stream_id,
        event=msgspec.convert(event, type=event_class, strict=False),
    )
