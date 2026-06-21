"""Agent run websocket event routes."""

from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.infrastructure.stream import iter_agent_run_events

router = APIRouter(prefix="/agents", tags=["agents"])


@router.websocket("/runs/{run_id}/events/ws")
async def watch_agent_run_events(
    websocket: WebSocket,
    run_id: UUID,
) -> None:
    """Stream agent run events to a websocket client."""
    await websocket.accept()
    last_event_id = websocket.query_params.get("last_event_id", "0-0")
    try:
        async for event_id, event in iter_agent_run_events(str(run_id), last_event_id):
            await websocket.send_json({"id": event_id, **event})
    except WebSocketDisconnect:
        return
