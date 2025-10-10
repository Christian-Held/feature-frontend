"""RAG API routes for website management and chat."""

from datetime import datetime
from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.api.deps import require_current_user
from backend.db.models.user import User
from backend.db.session import get_db
from backend.rag.api.schemas import (
    WebsiteCreate,
    WebsiteUpdate,
    WebsiteResponse,
    CustomQACreate,
    CustomQAUpdate,
    CustomQAResponse,
    ChatRequest,
    ChatResponse,
    CrawlResponse,
    UsageStatsResponse,
)
from backend.rag.models.website import Website, WebsiteStatus
from backend.rag.models.custom_qa import CustomQA
from backend.rag.models.usage_stat import UsageStat
from backend.rag.tasks.crawl import crawl_website_task
from backend.rag.query import RAGQueryService

router = APIRouter(prefix="/v1/rag", tags=["rag"])


# Website Management Endpoints (Authenticated)
@router.post("/websites", response_model=WebsiteResponse, status_code=status.HTTP_201_CREATED)
def create_website(
    website_data: WebsiteCreate,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    """Create a new website for RAG chatbot."""
    # Create website
    website = Website(
        user_id=current_user.id,
        url=str(website_data.url),
        name=website_data.name or str(website_data.url),
        status=WebsiteStatus.PENDING,
        brand_color=website_data.brand_color,
        logo_url=str(website_data.logo_url) if website_data.logo_url else None,
        welcome_message=website_data.welcome_message,
        position=website_data.position,
        language=website_data.language,
        crawl_frequency=website_data.crawl_frequency,
        max_pages=website_data.max_pages,
        is_active=True,
        pages_indexed=0,
    )

    session.add(website)
    session.commit()
    session.refresh(website)

    try:
        _ = crawl_website_task.delay(str(website.id))
    except Exception as exc:  # pragma: no cover - celery scheduling failure is rare
        website.status = WebsiteStatus.ERROR
        website.crawl_error = f"Failed to queue crawl: {exc}"
        session.commit()
        session.refresh(website)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to queue website crawl. Please try again.",
        ) from exc

    # Mark as crawling immediately so the UI can render progress while the task starts
    website.status = WebsiteStatus.CRAWLING
    website.crawl_error = None
    session.commit()
    session.refresh(website)

    return website


@router.get("/websites", response_model=List[WebsiteResponse])
def list_websites(
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    """List all websites for the current user."""
    result = session.execute(
        select(Website)
        .where(Website.user_id == current_user.id)
        .order_by(Website.created_at.desc())
    )
    websites = result.scalars().all()
    return websites


@router.get("/websites/{website_id}", response_model=WebsiteResponse)
def get_website(
    website_id: str,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    """Get a specific website."""
    result = session.execute(
        select(Website).where(
            Website.id == uuid.UUID(website_id),
            Website.user_id == current_user.id
        )
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    return website


@router.put("/websites/{website_id}", response_model=WebsiteResponse)
def update_website(
    website_id: str,
    website_data: WebsiteUpdate,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    """Update a website."""
    result = session.execute(
        select(Website).where(
            Website.id == uuid.UUID(website_id),
            Website.user_id == current_user.id
        )
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    # Update fields
    update_data = website_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "logo_url" and value:
            value = str(value)
        setattr(website, field, value)

    session.commit()
    session.refresh(website)

    return website


@router.delete("/websites/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_website(
    website_id: str,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    """Delete a website and all associated data."""
    result = session.execute(
        select(Website).where(
            Website.id == uuid.UUID(website_id),
            Website.user_id == current_user.id
        )
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    session.delete(website)
    session.commit()


@router.post("/websites/{website_id}/crawl", response_model=CrawlResponse)
def trigger_crawl(
    website_id: str,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    """Trigger a website crawl."""
    result = session.execute(
        select(Website).where(
            Website.id == uuid.UUID(website_id),
            Website.user_id == current_user.id
        )
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    if website.status == WebsiteStatus.CRAWLING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Crawl already in progress"
        )

    # Trigger async crawl task
    task = crawl_website_task.delay(str(website.id))

    return CrawlResponse(
        task_id=task.id,
        status="pending",
        message="Crawl task started"
    )


# Custom Q&A Endpoints
@router.post("/websites/{website_id}/qas", response_model=CustomQAResponse, status_code=status.HTTP_201_CREATED)
def create_custom_qa(
    website_id: str,
    qa_data: CustomQACreate,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    """Create a custom Q&A pair."""
    # Verify website ownership
    result = session.execute(
        select(Website).where(
            Website.id == uuid.UUID(website_id),
            Website.user_id == current_user.id
        )
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    qa = CustomQA(
        website_id=website.id,
        question=qa_data.question,
        answer=qa_data.answer,
        priority=qa_data.priority,
        category=qa_data.category,
        keywords=qa_data.keywords,
    )

    session.add(qa)
    session.commit()
    session.refresh(qa)

    return qa


@router.get("/websites/{website_id}/qas", response_model=List[CustomQAResponse])
def list_custom_qas(
    website_id: str,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    """List all custom Q&As for a website."""
    # Verify website ownership
    result = session.execute(
        select(Website).where(
            Website.id == uuid.UUID(website_id),
            Website.user_id == current_user.id
        )
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    result = session.execute(
        select(CustomQA)
        .where(CustomQA.website_id == website.id)
        .order_by(CustomQA.priority.desc(), CustomQA.created_at.desc())
    )
    qas = result.scalars().all()

    return qas


@router.delete("/websites/{website_id}/qas/{qa_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_qa(
    website_id: str,
    qa_id: str,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    """Delete a custom Q&A."""
    # Verify website ownership
    result = session.execute(
        select(Website).where(
            Website.id == uuid.UUID(website_id),
            Website.user_id == current_user.id
        )
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    result = session.execute(
        select(CustomQA).where(
            CustomQA.id == uuid.UUID(qa_id),
            CustomQA.website_id == website.id
        )
    )
    qa = result.scalar_one_or_none()

    if not qa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Q&A not found"
        )

    session.delete(qa)
    session.commit()


# Public Chat Endpoint (Token-based auth)
@router.post("/chat", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    authorization: str = Header(..., alias="X-Embed-Token"),
    session: Session = Depends(get_db),
):
    """Public chat endpoint for embedded widget (token-based auth)."""
    # Find website by embed token
    result = session.execute(
        select(Website).where(
            Website.embed_token == authorization,
            Website.is_active == True
        )
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid embed token"
        )

    # Get custom Q&As
    result = session.execute(
        select(CustomQA)
        .where(CustomQA.website_id == website.id)
        .order_by(CustomQA.priority.desc())
    )
    custom_qas = [
        {"question": qa.question, "answer": qa.answer}
        for qa in result.scalars().all()
    ]

    # Convert conversation history
    conversation_history = None
    if chat_request.conversation_history:
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in chat_request.conversation_history
        ]

    # Query RAG service (async methods)
    rag_service = RAGQueryService()
    response = await rag_service.answer_question(
        question=chat_request.question,
        website_id=str(website.id),
        conversation_history=conversation_history,
        custom_qas=custom_qas,
    )

    # Get suggested questions
    suggested = await rag_service.get_suggested_questions(
        website_id=str(website.id),
        limit=3
    )

    return ChatResponse(
        answer=response["answer"],
        sources=response["sources"],
        type=response["type"],
        confidence=response["confidence"],
        actions=response.get("actions"),
        suggested_questions=suggested,
    )


# Analytics Endpoint
@router.get("/websites/{website_id}/analytics", response_model=List[UsageStatsResponse])
def get_analytics(
    website_id: str,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    """Get usage analytics for a website."""
    # Verify website ownership
    result = session.execute(
        select(Website).where(
            Website.id == uuid.UUID(website_id),
            Website.user_id == current_user.id
        )
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    # Get stats
    result = session.execute(
        select(UsageStat)
        .where(UsageStat.website_id == website.id)
        .order_by(UsageStat.date.desc())
        .limit(30)  # Last 30 days
    )
    stats = result.scalars().all()

    return stats


__all__ = ["router"]
