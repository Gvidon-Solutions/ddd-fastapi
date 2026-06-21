"""Taskiq tasks for agent workflows."""

from app.infrastructure.taskiq.agent_runner import run_agent_workflow
from app.infrastructure.taskiq.broker import broker


@broker.task(task_name="agent.run_workflow")
async def run_agent_workflow_task(agent_run_id: str) -> str:
    """Execute one persisted agent workflow run."""
    return await run_agent_workflow(agent_run_id)
