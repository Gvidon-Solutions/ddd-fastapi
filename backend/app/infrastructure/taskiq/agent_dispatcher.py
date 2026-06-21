"""Dispatch agent workflow tasks to Taskiq."""

from app.domain.agent.value_objects import AgentRunId
from app.infrastructure.taskiq.agent_tasks import run_agent_workflow_task


async def enqueue_agent_workflow(agent_run_id: AgentRunId) -> str:
    """Queue an agent workflow execution task and return its Taskiq ID."""
    task = await run_agent_workflow_task.kiq(str(agent_run_id.value))
    return str(task.task_id)
