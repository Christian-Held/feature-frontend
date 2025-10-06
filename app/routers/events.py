from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.core.logging import get_logger
from app.services.job_events import stream_job_events

router = APIRouter()
logger = get_logger(__name__)


@router.websocket("/ws/jobs")
async def jobs_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("jobs_ws_connected", client=str(websocket.client))
    try:
        async for event in stream_job_events():
            await websocket.send_json({"type": event.type, "payload": event.payload})
    except WebSocketDisconnect:
        logger.info("jobs_ws_disconnected", client=str(websocket.client))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("jobs_ws_error", error=str(exc))
    finally:
        if websocket.application_state is not WebSocketState.DISCONNECTED:
            await websocket.close()
