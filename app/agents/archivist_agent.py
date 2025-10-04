from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List

from app.core.config import get_settings
from app.core.logging import get_logger

from app.context.memory_store import MemoryStore

logger = get_logger(__name__)


class ArchivistAgent:
    """Maintains long-term memory by compacting old notes."""

    def __init__(self, memory_store: MemoryStore | None = None):
        self.memory_store = memory_store or MemoryStore()
        self.settings = get_settings()

    def maintain(self, session, job_id: str) -> List[Dict[str, str]]:
        notes = self.memory_store.list_notes(session, job_id)
        if len(notes) <= self.settings.memory_max_items_per_job * 0.8:
            return []
        archived = []
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        snapshot = {"generated_at": timestamp, "notes": notes[:-10]}
        payload = json.dumps(snapshot, ensure_ascii=False, indent=2)
        filename = f"archive_{timestamp}.json"
        path, size = self.memory_store.add_file(session, job_id, filename, payload.encode("utf-8"))
        for stale in notes[:-10]:
            # remove archived notes
            self._delete_note(session, job_id, stale)
        archived.append({"path": path, "bytes": size})
        logger.info("archivist_compacted", job_id=job_id, items=len(snapshot["notes"]))
        return archived

    def _delete_note(self, session, job_id: str, payload: Dict[str, str]) -> None:
        from app.db.models import MemoryItemModel

        session.query(MemoryItemModel).filter(
            MemoryItemModel.job_id == job_id,
            MemoryItemModel.key == payload.get("title"),
        ).delete()
        session.flush()
