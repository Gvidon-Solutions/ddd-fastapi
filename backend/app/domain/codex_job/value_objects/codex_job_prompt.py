"""Define the Codex job prompt value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CodexJobPrompt:
    """Represent a Codex job prompt."""

    value: str

    def __post_init__(self) -> None:
        """Validate prompt text."""
        if not self.value.strip():
            raise ValueError("Codex job prompt must not be empty")
