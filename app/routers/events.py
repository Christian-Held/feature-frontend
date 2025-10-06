from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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
    except RuntimeError as exc:
        if "close message has been sent" in str(exc):
            logger.info("jobs_ws_already_closed", client=str(websocket.client))
        else:
            logger.exception("jobs_ws_runtime_error", error=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("jobs_ws_error", error=str(exc))
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
