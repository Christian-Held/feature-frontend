from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import MemoryFileModel, MemoryItemModel

from .notes import Note, deserialize_note, serialize_note

logger = get_logger(__name__)


class MemoryLimitError(RuntimeError):
    """Raised when memory limits are exceeded."""


class MemoryStore:
    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or Path("./memory")
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.settings = get_settings()

    def _job_dir(self, job_id: str) -> Path:
        job_dir = self.base_path / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def list_notes(self, session: Session, job_id: str) -> List[Dict[str, Any]]:
        records = (
            session.query(MemoryItemModel)
            .filter(MemoryItemModel.job_id == job_id)
            .order_by(MemoryItemModel.created_at.asc())
            .all()
        )
        notes: List[Dict[str, Any]] = []
        for record in records:
            try:
                raw_payload = json.loads(record.content)
                payload = serialize_note(deserialize_note(raw_payload))
            except Exception:  # pragma: no cover - fallback for legacy entries
                payload = {"type": record.kind, "title": record.key, "body": record.content}
            notes.append(payload)
        return notes

    def add_note(self, session: Session, job_id: str, note_payload: Dict[str, Any]) -> Dict[str, Any]:
        note = Note.from_dict(note_payload)
        existing_count = (
            session.query(func.count(MemoryItemModel.id))
            .filter(MemoryItemModel.job_id == job_id)
            .scalar()
        )
        if existing_count >= self.settings.memory_max_items_per_job:
            raise MemoryLimitError("Memory item limit exceeded")
        content_bytes = len(note.body.encode("utf-8"))
        if content_bytes > self.settings.memory_max_bytes_per_item:
            raise MemoryLimitError("Memory item exceeds byte budget")
        record = MemoryItemModel(
            job_id=job_id,
            kind=note.note_type,
            key=note.title,
            content=json.dumps(note.to_dict(), ensure_ascii=False),
        )
        session.add(record)
        session.flush()
        logger.info("memory_note_added", job_id=job_id, note_type=note.note_type, title=note.title)
        return note.to_dict()

    def list_files(self, session: Session, job_id: str) -> List[Dict[str, Any]]:
        records = (
            session.query(MemoryFileModel)
            .filter(MemoryFileModel.job_id == job_id)
            .order_by(MemoryFileModel.created_at.asc())
            .all()
        )
        result: List[Dict[str, Any]] = []
        for record in records:
            result.append({
                "path": record.path,
                "bytes": len(record.bytes or b""),
                "created_at": record.created_at.isoformat() if record.created_at else None,
            })
        return result

    def add_file(self, session: Session, job_id: str, filename: str, data: bytes) -> Tuple[str, int]:
        job_dir = self._job_dir(job_id)
        path = job_dir / filename
        path.write_bytes(data)
        record = MemoryFileModel(job_id=job_id, path=str(path), bytes=data)
        session.add(record)
        session.flush()
        logger.info("memory_file_added", job_id=job_id, path=str(path), size=len(data))
        return str(path), len(data)

    def get_memory(self, session: Session, job_id: str) -> Dict[str, Any]:
        return {"notes": self.list_notes(session, job_id), "files": self.list_files(session, job_id)}
