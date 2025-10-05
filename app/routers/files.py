from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.core.logging import get_logger

router = APIRouter(prefix="/api/files", tags=["files"])
logger = get_logger(__name__)
_ROOT = Path("./data")
_ROOT.mkdir(parents=True, exist_ok=True)


class FileEntry(BaseModel):
    path: str
    name: str
    type: str
    size: int
    modifiedAt: str


def _resolve_path(path: str) -> Path:
    safe_path = path.strip("/")
    target = (_ROOT / safe_path).resolve()
    root = _ROOT.resolve()
    if not str(target).startswith(str(root)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    return target


def _format_timestamp(mtime: float) -> str:
    return datetime.fromtimestamp(mtime).isoformat()


@router.get("", response_model=List[FileEntry])
def list_files(path: str = Query("/")) -> List[FileEntry]:
    base = _resolve_path(path)
    if not base.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Path not found")

    if base.is_file():
        stats = base.stat()
        return [
            FileEntry(
                path=str(base.relative_to(_ROOT)),
                name=base.name,
                type="file",
                size=stats.st_size,
                modifiedAt=_format_timestamp(stats.st_mtime),
            )
        ]

    entries: List[FileEntry] = []
    for item in sorted(base.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        stats = item.stat()
        entry_type = "file" if item.is_file() else "directory"
        entries.append(
            FileEntry(
                path=str(item.relative_to(_ROOT)),
                name=item.name,
                type=entry_type,
                size=stats.st_size,
                modifiedAt=_format_timestamp(stats.st_mtime),
            )
        )
    return entries
