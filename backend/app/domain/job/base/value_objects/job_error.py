"""Define the JobError value object."""

from __future__ import annotations

from dataclasses import dataclass, field

JSONValue = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]


@dataclass(frozen=True)
class JobError:
    """Represent a job failure."""

    code: str
    message: str
    details: dict[str, JSONValue] = field(default_factory=dict)
    retryable: bool = False

    def __post_init__(self) -> None:
        """Normalize omitted details to an empty mapping."""
        if self.details is None:
            object.__setattr__(self, "details", {})
