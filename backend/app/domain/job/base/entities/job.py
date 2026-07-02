"""Define the generic Job entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TypeVar
from uuid import UUID

from app.domain.job.base.value_objects import Initiator, JobError, JobStage, JobStatus

InputT = TypeVar("InputT")
ResultT = TypeVar("ResultT")


@dataclass(init=False)
class Job[InputT, ResultT]:
    """Represent one execution of a versioned job contract."""

    id: UUID
    type: str
    version: str
    name: str | None
    description: str | None
    input: InputT
    result: ResultT | None
    status: JobStatus
    initiator: Initiator
    parent_job_id: UUID | None
    requested_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: JobError | None
    _legacy_stage: JobStage | None = field(default=None, compare=False)

    def __init__(
        self,
        id: UUID | None = None,
        type: str | None = None,
        version: str = "v1",
        name: str | None = None,
        description: str | None = None,
        input: InputT | None = None,
        result: ResultT | None = None,
        status: JobStatus | None = None,
        initiator: Initiator | None = None,
        parent_job_id: UUID | None = None,
        requested_at: datetime | None = None,
        updated_at: datetime | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        error: JobError | None = None,
        *,
        job_id: UUID | None = None,
        job_type: str | None = None,
        job_name: str | None = None,
        job_description: str | None = None,
        job_input: object | None = None,
        job_status: JobStatus | None = None,
        job_stage: JobStage | None = None,
        result_summary: object | None = None,
        root_initiator: Initiator | None = None,
        job_error: JobError | None = None,
    ) -> None:
        """Create a job from either target or legacy field names."""
        self.id = id if id is not None else _required(job_id, "id")
        self.type = _normalize_type(type if type is not None else job_type)
        self.version = version
        self.name = name if name is not None else job_name
        self.description = description if description is not None else job_description
        self.input = _coerce_legacy_input(self.type, input, job_input)
        self.result = _coerce_legacy_result(self.type, result, result_summary)
        self.status = status if status is not None else _required(job_status, "status")
        self.initiator = (
            initiator if initiator is not None else _required(root_initiator, "initiator")
        )
        self.parent_job_id = parent_job_id
        self.requested_at = _required(requested_at, "requested_at")
        self.updated_at = _required(updated_at, "updated_at")
        self.started_at = started_at
        self.finished_at = finished_at
        self.error = error if error is not None else job_error
        self._legacy_stage = job_stage

    @property
    def job_id(self) -> UUID:
        """Return the legacy job ID name."""
        return self.id

    @job_id.setter
    def job_id(self, value: UUID) -> None:
        self.id = value

    @property
    def job_type(self) -> str:
        """Return the legacy job type name."""
        return _legacy_type(self.type)

    @job_type.setter
    def job_type(self, value: str) -> None:
        self.type = _normalize_type(value)

    @property
    def job_name(self) -> str:
        """Return the legacy display name."""
        return self.name or self.type

    @job_name.setter
    def job_name(self, value: str | None) -> None:
        self.name = value

    @property
    def job_description(self) -> str | None:
        """Return the legacy description name."""
        return self.description

    @job_description.setter
    def job_description(self, value: str | None) -> None:
        self.description = value

    @property
    def job_input(self) -> dict | None:
        """Return input as a JSON-like legacy mapping when possible."""
        return _object_to_dict(self.input)

    @job_input.setter
    def job_input(self, value: object | None) -> None:
        self.input = _coerce_legacy_input(self.type, None, value)

    @property
    def job_status(self) -> JobStatus:
        """Return the legacy status name."""
        return self.status

    @job_status.setter
    def job_status(self, value: JobStatus) -> None:
        self.status = value

    @property
    def job_stage(self) -> JobStage | None:
        """Return transient legacy stage data for old call sites."""
        return self._legacy_stage

    @job_stage.setter
    def job_stage(self, value: JobStage | None) -> None:
        self._legacy_stage = value

    @property
    def result_summary(self) -> dict | None:
        """Return result as a JSON-like legacy mapping when possible."""
        return _object_to_dict(self.result)

    @result_summary.setter
    def result_summary(self, value: object | None) -> None:
        self.result = _coerce_legacy_result(self.type, None, value)

    @property
    def root_initiator(self) -> Initiator:
        """Return the legacy initiator name."""
        return self.initiator

    @root_initiator.setter
    def root_initiator(self, value: Initiator) -> None:
        self.initiator = value

    @property
    def job_error(self) -> JobError | None:
        """Return the legacy error name."""
        return self.error

    @job_error.setter
    def job_error(self, value: JobError | None) -> None:
        self.error = value


type AnyJob = Job[object, object]


def _required(value, name: str):
    if value is None:
        raise TypeError(f"Job requires {name}")
    return value


def _normalize_type(value: str | None) -> str:
    if value is None:
        raise TypeError("Job requires type")
    if value == "codex_run":
        return "codex.run"
    if value == "codex_auth":
        return "codex.auth"
    return value


def _legacy_type(value: str) -> str:
    if value == "codex.run":
        return "codex_run"
    if value == "codex.auth":
        return "codex_auth"
    return value


def _coerce_legacy_input(job_type: str, input_value, legacy_value):
    value = input_value if input_value is not None else legacy_value
    if value is None:
        if job_type == "codex.auth":
            from app.domain.job.codex_auth_job_use_case import CodexAuthInputV1

            return CodexAuthInputV1()
        return value
    if job_type == "codex.run" and isinstance(value, dict):
        from app.domain.job.codex_run_job_use_case import CodexRunInputV1

        return CodexRunInputV1(**value)
    if job_type == "codex.auth" and isinstance(value, dict):
        from app.domain.job.codex_auth_job_use_case import CodexAuthInputV1

        return CodexAuthInputV1(**value)
    return value


def _coerce_legacy_result(job_type: str, result_value, legacy_value):
    value = result_value if result_value is not None else legacy_value
    if value is None:
        return None
    if job_type == "codex.run" and isinstance(value, dict):
        from app.domain.job.codex_run_job_use_case import CodexRunResultV1

        try:
            return CodexRunResultV1(**value)
        except TypeError:
            return value
    if job_type == "codex.auth" and isinstance(value, dict):
        from app.domain.job.codex_auth_job_use_case import CodexAuthResultV1

        try:
            return CodexAuthResultV1(**value)
        except TypeError:
            return value
    return value


def _object_to_dict(value) -> dict | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    from dataclasses import asdict, is_dataclass

    if is_dataclass(value):
        return {
            key: item
            for key, item in asdict(value).items()
            if item is not None
        }
    return value
