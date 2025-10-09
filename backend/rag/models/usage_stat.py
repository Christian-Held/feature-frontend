"""UsageStat model for tracking daily usage metrics."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from backend.db.types import GUID


class UsageStat(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Daily aggregated usage statistics for a website."""

    __tablename__ = "rag_usage_stats"
    __table_args__ = (
        UniqueConstraint("website_id", "date", name="uix_website_date"),
    )

    # Parent website
    website_id: Mapped[GUID] = mapped_column(
        ForeignKey("rag_websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Date for this stat
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Conversation metrics
    conversations_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    messages_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Token usage
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Cost tracking
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), default=0.0, nullable=False)

    # Quality metrics
    avg_satisfaction_rating: Mapped[float | None] = mapped_column(Numeric(3, 2))
    total_ratings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    website: Mapped["Website"] = relationship("Website", back_populates="usage_stats")

    def __repr__(self) -> str:
        return f"<UsageStat(website_id={self.website_id}, date={self.date}, conversations={self.conversations_count})>"
