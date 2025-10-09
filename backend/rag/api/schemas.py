"""Pydantic schemas for RAG API."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, HttpUrl


# Website Management Schemas
class WebsiteCreate(BaseModel):
    url: HttpUrl
    name: Optional[str] = None
    brand_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    logo_url: Optional[HttpUrl] = None
    welcome_message: Optional[str] = None
    position: str = "BOTTOM_RIGHT"
    language: Optional[str] = "en"
    crawl_frequency: str = "MANUAL"
    max_pages: int = Field(default=100, ge=1, le=1000)


class WebsiteUpdate(BaseModel):
    name: Optional[str] = None
    brand_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    logo_url: Optional[HttpUrl] = None
    welcome_message: Optional[str] = None
    position: Optional[str] = None
    language: Optional[str] = None
    crawl_frequency: Optional[str] = None
    max_pages: Optional[int] = Field(None, ge=1, le=1000)
    is_active: Optional[bool] = None


class WebsiteResponse(BaseModel):
    id: str
    user_id: str
    url: str
    name: Optional[str]
    status: str
    embed_token: str
    brand_color: Optional[str]
    logo_url: Optional[str]
    welcome_message: Optional[str]
    position: str
    language: Optional[str]
    crawl_frequency: str
    max_pages: int
    is_active: bool
    last_crawled_at: Optional[datetime]
    pages_indexed: int
    crawl_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Custom Q&A Schemas
class CustomQACreate(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    answer: str = Field(..., min_length=1, max_length=2000)
    priority: int = Field(default=0, ge=0, le=100)
    category: Optional[str] = None
    keywords: Optional[str] = None


class CustomQAUpdate(BaseModel):
    question: Optional[str] = Field(None, min_length=1, max_length=500)
    answer: Optional[str] = Field(None, min_length=1, max_length=2000)
    priority: Optional[int] = Field(None, ge=0, le=100)
    category: Optional[str] = None
    keywords: Optional[str] = None


class CustomQAResponse(BaseModel):
    id: str
    website_id: str
    question: str
    answer: str
    priority: int
    category: Optional[str]
    keywords: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Chat Schemas
class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    conversation_history: Optional[List[ChatMessage]] = None
    visitor_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    type: str  # "custom_qa", "rag", "no_context"
    confidence: str  # "high", "medium", "low", "none"
    actions: Optional[Dict[str, Any]] = None
    suggested_questions: Optional[List[str]] = None


# Analytics Schemas
class UsageStatsResponse(BaseModel):
    date: str
    conversations_count: int
    messages_count: int
    tokens_used: int
    cost_usd: float
    avg_satisfaction_rating: Optional[float]
    total_ratings: int

    class Config:
        from_attributes = True


# Crawl Trigger Schema
class CrawlResponse(BaseModel):
    task_id: str
    status: str
    message: str
