"""Define the agent prompt value object."""

from dataclasses import dataclass

MAX_PROMPT_LENGTH = 20000
PROMPT_REQUIRED_ERROR_MESSAGE = "Prompt is required"
PROMPT_TOO_LONG_ERROR_MESSAGE = "Prompt must be 20000 characters or less"


@dataclass(frozen=True)
class AgentPrompt:
    """Represent the user input for an agent workflow."""

    value: str

    def __post_init__(self) -> None:
        """Validate prompt constraints."""
        if not self.value:
            raise ValueError(PROMPT_REQUIRED_ERROR_MESSAGE)
        if len(self.value) > MAX_PROMPT_LENGTH:
            raise ValueError(PROMPT_TOO_LONG_ERROR_MESSAGE)

    def __str__(self) -> str:
        """Return the wrapped prompt string."""
        return self.value
