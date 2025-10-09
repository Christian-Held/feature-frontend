"""WebsitePage model for storing crawled pages."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from backend.db.types import GUID


class WebsitePage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents a single crawled page from a website."""

    __tablename__ = "rag_website_pages"

    # Parent website
    website_id: Mapped[GUID] = mapped_column(
        ForeignKey("rag_websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Page details
    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Cleaned plain text

    # Metadata extracted from page
    page_metadata: Mapped[dict | None] = mapped_column(JSON)  # headings, images, links, etc.

    # Vector database reference
    embedding_ids: Mapped[dict | None] = mapped_column(JSON)  # {chunk_index: vector_id}

    # Crawl info
    last_crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    content_hash: Mapped[str | None] = mapped_column(String(64))  # SHA256 to detect changes

    # Relationships
    website: Mapped["Website"] = relationship("Website", back_populates="pages")

    def __repr__(self) -> str:
        return f"<WebsitePage(id={self.id}, url={self.url})>"
