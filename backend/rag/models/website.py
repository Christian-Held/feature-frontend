"""Website model for RAG system."""

from __future__ import annotations

import enum
import secrets
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from backend.db.types import GUID


class WebsiteStatus(str, enum.Enum):
    """Status of website crawling/indexing."""
    PENDING = "PENDING"
    CRAWLING = "CRAWLING"
    READY = "READY"
    ERROR = "ERROR"
    PAUSED = "PAUSED"


class ChatbotPosition(str, enum.Enum):
    """Position of chatbot widget on website."""
    BOTTOM_RIGHT = "BOTTOM_RIGHT"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    TOP_RIGHT = "TOP_RIGHT"
    TOP_LEFT = "TOP_LEFT"


class CrawlFrequency(str, enum.Enum):
    """How often to re-crawl website."""
    MANUAL = "MANUAL"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


def generate_embed_token() -> str:
    """Generate a secure embed token."""
    return f"pk_{'live' if True else 'test'}_{secrets.token_urlsafe(32)}"


class Website(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents a website managed by a user with AI chatbot enabled."""

    __tablename__ = "rag_websites"

    # Owner
    user_id: Mapped[GUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Website details
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[WebsiteStatus] = mapped_column(
        Enum(WebsiteStatus, name="website_status"),
        default=WebsiteStatus.PENDING,
        nullable=False,
        index=True
    )

    # Embed token for authentication
    embed_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        default=generate_embed_token
    )

    # Customization
    brand_color: Mapped[str | None] = mapped_column(String(7))  # #RRGGBB
    logo_url: Mapped[str | None] = mapped_column(String(2048))
    welcome_message: Mapped[str | None] = mapped_column(Text)
    position: Mapped[ChatbotPosition] = mapped_column(
        Enum(ChatbotPosition, name="chatbot_position"),
        default=ChatbotPosition.BOTTOM_RIGHT,
        nullable=False
    )

    # Settings
    language: Mapped[str | None] = mapped_column(String(10), default="en")  # ISO 639-1 code
    crawl_frequency: Mapped[CrawlFrequency] = mapped_column(
        Enum(CrawlFrequency, name="crawl_frequency"),
        default=CrawlFrequency.MANUAL,
        nullable=False
    )
    max_pages: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Crawl status
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pages_indexed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    crawl_error: Mapped[str | None] = mapped_column(Text)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="rag_websites")
    pages: Mapped[list["WebsitePage"]] = relationship("WebsitePage", back_populates="website", cascade="all, delete-orphan")
    custom_qas: Mapped[list["CustomQA"]] = relationship("CustomQA", back_populates="website", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="website", cascade="all, delete-orphan")
    usage_stats: Mapped[list["UsageStat"]] = relationship("UsageStat", back_populates="website", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Website(id={self.id}, url={self.url}, status={self.status})>"
