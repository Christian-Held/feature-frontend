"""CustomQA model for user-defined Q&A pairs."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from backend.db.types import GUID


class CustomQA(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User-defined question-answer pairs for a website."""

    __tablename__ = "rag_custom_qas"

    # Parent website
    website_id: Mapped[GUID] = mapped_column(
        ForeignKey("rag_websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Q&A content
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    # Priority for matching (higher = checked first)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Optional metadata
    category: Mapped[str | None] = mapped_column(String(100))  # e.g., "hours", "contact", "services"
    keywords: Mapped[str | None] = mapped_column(Text)  # Comma-separated keywords for matching

    # Relationships
    website: Mapped["Website"] = relationship("Website", back_populates="custom_qas")

    def __repr__(self) -> str:
        return f"<CustomQA(id={self.id}, question={self.question[:30]}...)>"
