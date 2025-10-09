"""Conversation model for tracking chat sessions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from backend.db.types import GUID


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents a chat conversation on a website."""

    __tablename__ = "rag_conversations"

    # Parent website
    website_id: Mapped[GUID] = mapped_column(
        ForeignKey("rag_websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Visitor identification
    visitor_id: Mapped[str | None] = mapped_column(String(255), index=True)  # Anonymous or tracked
    visitor_ip: Mapped[str | None] = mapped_column(String(45))
    visitor_user_agent: Mapped[str | None] = mapped_column(Text)

    # Conversation metadata
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Messages in the conversation
    messages: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    # Structure: [{"role": "user"/"assistant", "content": "...", "timestamp": "...", "actions": {...}}]

    # Feedback
    satisfaction_rating: Mapped[int | None] = mapped_column(Integer)  # 1-5 stars
    feedback_text: Mapped[str | None] = mapped_column(Text)

    # Token usage for this conversation
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    website: Mapped["Website"] = relationship("Website", back_populates="conversations")

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, website_id={self.website_id}, started_at={self.started_at})>"
