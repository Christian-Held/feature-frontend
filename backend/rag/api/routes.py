"""RAG API routes for website management and chat."""

from datetime import datetime
from typing import List
import json
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.api.deps import require_current_user
from backend.db.models.user import User
from backend.db.session import get_db
from backend.rag.api.schemas import (
    WebsiteCreate,
    WebsiteUpdate,
    WebsiteResponse,
    WebsitePageCollectionResponse,
    WebsitePageResponse,
    CrawlExportInfo,
    CustomQACreate,
    CustomQAUpdate,
    CustomQAResponse,
    ChatRequest,
    ChatResponse,
    CrawlResponse,
    UsageStatsResponse,
)
from backend.rag.models.website import Website, WebsiteStatus
from backend.rag.models.website_page import WebsitePage
from backend.rag.models.custom_qa import CustomQA
from backend.rag.models.usage_stat import UsageStat
from backend.core.config import get_settings
from backend.rag.tasks.crawl import (
    crawl_website_task,
    run_crawl_inline,
    get_latest_export_path,
)
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

    settings = get_settings()
    use_celery = settings.rag_task_execution_mode == "celery"
    crawl_result: dict | None = None

    try:
        if use_celery:
            _ = crawl_website_task.delay(str(website.id))
        else:
            crawl_result = run_crawl_inline(str(website.id))
    except Exception as exc:  # pragma: no cover - celery scheduling failure is rare
        website.status = WebsiteStatus.ERROR
        website.crawl_error = f"Failed to start crawl: {exc}"
        session.commit()
        session.refresh(website)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to queue website crawl. Please try again.",
        ) from exc

    if use_celery:
        # Mark as crawling immediately so the UI can render progress while the task starts
        website.status = WebsiteStatus.CRAWLING
        website.crawl_error = None
        session.commit()
        session.refresh(website)
    else:
        # Inline crawl already updated website state; refresh to return latest data
        session.refresh(website)
        if crawl_result and not crawl_result.get("success", False):
            website.crawl_error = crawl_result.get("error", "Unknown crawl error")
            session.commit()
            session.refresh(website)

    return website


@router.get("/websites/{website_id}/pages", response_model=WebsitePageCollectionResponse)
def list_website_pages(
    website_id: str,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    """Return crawled pages for a website along with latest export metadata."""

    website_result = session.execute(
        select(Website).where(
            Website.id == uuid.UUID(website_id),
            Website.user_id == current_user.id
        )
    )
    website = website_result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    result = session.execute(
        select(WebsitePage)
        .where(WebsitePage.website_id == website.id)
        .order_by(WebsitePage.last_crawled_at.desc())
    )
    pages = result.scalars().all()

    page_payloads = [
        WebsitePageResponse(
            id=page.id,
            url=page.url,
            title=page.title,
            content=page.content,
            content_preview=_build_content_preview(page.content),
            word_count=len(page.content.split()),
            page_metadata=page.page_metadata,
            last_crawled_at=page.last_crawled_at,
            created_at=page.created_at,
            updated_at=page.updated_at,
        )
        for page in pages
    ]

    export_path = get_latest_export_path(website.id)
    export_info: CrawlExportInfo | None = None

    if export_path and export_path.exists():
        metadata = _load_export_metadata(export_path)
        export_info = CrawlExportInfo(
            filename=export_path.name,
            crawled_at=metadata.get("crawled_at"),
            page_count=metadata.get("page_count"),
        )

    return WebsitePageCollectionResponse(pages=page_payloads, export=export_info)


@router.get("/websites/{website_id}/pages/export")
def download_crawl_export(
    website_id: str,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db),
):
    """Download the latest crawl snapshot for a website."""

    website_result = session.execute(
        select(Website).where(
            Website.id == uuid.UUID(website_id),
            Website.user_id == current_user.id
        )
    )
    website = website_result.scalar_one_or_none()

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    export_path = get_latest_export_path(website.id)

    if not export_path or not export_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No crawl export available yet"
        )

    filename = _build_export_filename(website, export_path)

    return FileResponse(
        export_path,
        media_type="application/json",
        filename=filename,
    )


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

    settings = get_settings()
    use_celery = settings.rag_task_execution_mode == "celery"

    if use_celery:
        try:
            website.status = WebsiteStatus.CRAWLING
            website.crawl_error = None
            session.commit()
            task = crawl_website_task.delay(str(website.id))
        except Exception as exc:  # pragma: no cover - rare scheduling failure
            website.status = WebsiteStatus.ERROR
            website.crawl_error = f"Failed to start crawl: {exc}"
            session.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to queue website crawl. Please try again.",
            ) from exc

        return CrawlResponse(
            task_id=task.id,
            status="pending",
            message="Crawl task started"
        )

    crawl_result = run_crawl_inline(str(website.id))
    session.refresh(website)

    if not crawl_result.get("success", False):
        error_message = crawl_result.get("error", "Website crawl failed")
        return CrawlResponse(
            task_id="inline",
            status="error",
            message=error_message
        )

    return CrawlResponse(
        task_id="inline",
        status="completed",
        message="Crawl completed successfully"
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
    embed_token: str = Header(..., alias="X-Embed-Token"),
    session: Session = Depends(get_db),
):
    """Public chat endpoint for embedded widget (token-based auth)."""
    # Find website by embed token
    result = session.execute(
        select(Website).where(
            Website.embed_token == embed_token,
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


def _build_content_preview(text: str, max_length: int = 320) -> str:
    collapsed = re.sub(r"\s+", " ", text or "").strip()
    if len(collapsed) <= max_length:
        return collapsed
    return f"{collapsed[:max_length].rstrip()}…"


def _load_export_metadata(export_path: Path) -> dict[str, Any]:
    try:
        with export_path.open("r", encoding="utf-8") as export_file:
            data = json.load(export_file)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    return {
        "crawled_at": data.get("crawled_at"),
        "page_count": data.get("page_count"),
    }


def _normalize_export_timestamp(value: str | None) -> str:
    if not value:
        return "latest"

    normalized = value.replace(":", "").replace("-", "")
    normalized = normalized.replace(".", "").replace("+", "")
    normalized = normalized.replace("Z", "Z").replace("T", "T")
    safe = re.sub(r"[^0-9TZ]", "", normalized)
    return safe or "latest"


def _build_export_filename(website: Website, export_path: Path) -> str:
    base_name = website.name or website.url
    safe_base = re.sub(r"[^A-Za-z0-9]+", "-", base_name).strip("-") if base_name else ""

    if not safe_base:
        safe_base = str(website.id)

    metadata = _load_export_metadata(export_path)
    timestamp_hint = metadata.get("crawled_at") if metadata else None

    if not timestamp_hint and export_path.stem != "latest":
        timestamp_hint = export_path.stem

    safe_timestamp = _normalize_export_timestamp(timestamp_hint)

    return f"{safe_base}-crawl-{safe_timestamp}.json"


__all__ = ["router"]
