from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import deps
from app.context.memory_store import MemoryLimitError, MemoryStore
from app.core.logging import get_logger

router = APIRouter(prefix="/memory", tags=["memory"])
logger = get_logger(__name__)


class MemoryNoteRequest(BaseModel):
    type: str
    title: str
    body: str
    tags: list[str] | None = None
    stepId: str | None = None


class MemoryResponse(BaseModel):
    notes: list
    files: list


@router.post("/{job_id}/notes", status_code=status.HTTP_201_CREATED)
def add_note(job_id: str, payload: MemoryNoteRequest, session: Session = Depends(deps.get_db)):
    store = MemoryStore()
    try:
        note = store.add_note(session, job_id, payload.dict(exclude_none=True))
    except MemoryLimitError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    logger.info("memory_note_created", job_id=job_id, title=payload.title)
    return note


@router.get("/{job_id}", response_model=MemoryResponse)
def get_memory(job_id: str, session: Session = Depends(deps.get_db)) -> MemoryResponse:
    store = MemoryStore()
    memory = store.get_memory(session, job_id)
    return MemoryResponse(**memory)


@router.post("/{job_id}/files", status_code=status.HTTP_201_CREATED)
async def upload_file(job_id: str, request: Request, session: Session = Depends(deps.get_db)):
    try:
        form = await request.form()
    except RuntimeError as exc:
        logger.error("memory_file_upload_failed", reason="python-multipart missing", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="python-multipart ist nicht installiert. Bitte Abhängigkeit hinzufügen, um Datei-Uploads zu aktivieren.",
        ) from exc

    upload = form.get("file")
    if not isinstance(upload, UploadFile):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Feld 'file' fehlt oder ist ungültig.")

    data = await upload.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    store = MemoryStore()
    path, size = store.add_file(session, job_id, upload.filename, data)
    session.commit()
    logger.info("memory_file_uploaded", job_id=job_id, path=path, size=size)
    return {"path": path, "bytes": size}
