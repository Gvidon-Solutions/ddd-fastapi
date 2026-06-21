"""Resolve agent workflow runners by workflow name."""

from app.config import settings
from app.domain.agent.value_objects import AgentWorkflowName
from app.infrastructure.openai_agents.codex_workflow_runner import (
    CodexWorkflowRunner,
    DisabledCodexWorkflowRunner,
)
from app.usecase.agent import AgentWorkflowRunner


def new_agent_workflow_runner(
    workflow_name: AgentWorkflowName,
) -> AgentWorkflowRunner:
    """Create a workflow runner for a registered workflow name."""
    if workflow_name.value == "codex" or workflow_name.value.startswith("codex_"):
        if settings.CODEX_WORKFLOW_ENABLED:
            return CodexWorkflowRunner()
        return DisabledCodexWorkflowRunner()
    return DisabledCodexWorkflowRunner()
