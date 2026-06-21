"""Define the agent event payload value object."""

from dataclasses import dataclass
from typing import Any

PayloadValue = (
    str | int | float | bool | None | list["PayloadValue"] | dict[str, "PayloadValue"]
)

PAYLOAD_REQUIRED_ERROR_MESSAGE = "Event payload is required"


@dataclass(frozen=True)
class AgentEventPayload:
    """Represent JSON-serializable agent event data."""

    value: dict[str, PayloadValue]

    def __post_init__(self) -> None:
        """Validate event payload constraints."""
        if not self.value:
            raise ValueError(PAYLOAD_REQUIRED_ERROR_MESSAGE)
        self._ensure_json_value(self.value)

    @classmethod
    def _ensure_json_value(cls, value: Any) -> None:
        """Raise when a value is not JSON-serializable by shape."""
        if value is None or isinstance(value, str | int | float | bool):
            return
        if isinstance(value, list):
            for item in value:
                cls._ensure_json_value(item)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError("Event payload keys must be strings")
                cls._ensure_json_value(item)
            return
        raise ValueError("Event payload must be JSON-serializable")
