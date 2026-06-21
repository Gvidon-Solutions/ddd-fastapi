"""Define the agent workflow name value object."""

from dataclasses import dataclass

MAX_WORKFLOW_NAME_LENGTH = 120
WORKFLOW_NAME_REQUIRED_ERROR_MESSAGE = "Workflow name is required"
WORKFLOW_NAME_TOO_LONG_ERROR_MESSAGE = "Workflow name must be 120 characters or less"


@dataclass(frozen=True)
class AgentWorkflowName:
    """Represent a registered agent workflow name."""

    value: str

    def __post_init__(self) -> None:
        """Validate workflow name constraints."""
        if not self.value:
            raise ValueError(WORKFLOW_NAME_REQUIRED_ERROR_MESSAGE)
        if len(self.value) > MAX_WORKFLOW_NAME_LENGTH:
            raise ValueError(WORKFLOW_NAME_TOO_LONG_ERROR_MESSAGE)

    def __str__(self) -> str:
        """Return the wrapped workflow name string."""
        return self.value
