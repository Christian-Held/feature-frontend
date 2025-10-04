from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
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
def upload_file(job_id: str, file: UploadFile = File(...), session: Session = Depends(deps.get_db)):
    store = MemoryStore()
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    path, size = store.add_file(session, job_id, file.filename, data)
    session.commit()
    logger.info("memory_file_uploaded", job_id=job_id, path=path, size=size)
    return {"path": path, "bytes": size}
