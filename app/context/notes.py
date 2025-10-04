from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List

ALLOWED_NOTE_TYPES = {"Decision", "Constraint", "Todo", "Glossary", "Link"}


class NoteValidationError(ValueError):
    """Raised when a note does not conform to the schema."""


@dataclass(slots=True)
class Note:
    note_type: str
    title: str
    body: str
    tags: List[str] = field(default_factory=list)
    step_id: str | None = None

    def __post_init__(self) -> None:
        if self.note_type not in ALLOWED_NOTE_TYPES:
            raise NoteValidationError(f"Invalid note type '{self.note_type}'")
        if not self.title.strip():
            raise NoteValidationError("Title must not be empty")
        if not self.body.strip():
            raise NoteValidationError("Body must not be empty")
        if any(not tag.strip() for tag in self.tags):
            raise NoteValidationError("Tags must not be empty")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.note_type,
            "title": self.title,
            "body": self.body,
            "tags": list(self.tags),
            "stepId": self.step_id,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Note":
        try:
            note_type = payload["type"]
            title = payload["title"]
            body = payload["body"]
        except KeyError as exc:  # pragma: no cover - defensive
            raise NoteValidationError(f"Missing note field: {exc.args[0]}") from exc
        tags = payload.get("tags", [])
        if not isinstance(tags, Iterable) or isinstance(tags, (str, bytes)):
            raise NoteValidationError("Tags must be a list")
        step_id = payload.get("stepId")
        return cls(note_type=note_type, title=title, body=body, tags=list(tags), step_id=step_id)


def serialize_note(note: Note) -> Dict[str, Any]:
    return note.to_dict()


def deserialize_note(payload: Dict[str, Any]) -> Note:
    return Note.from_dict(payload)
