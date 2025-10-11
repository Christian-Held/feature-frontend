"""Celery tasks for website crawling and embedding generation."""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
import uuid

from sqlalchemy import select, func
from backend.core.config import get_settings
from backend.db.session import SessionLocal
from backend.rag.models.website import Website, WebsiteStatus
from backend.rag.models.website_page import WebsitePage
from backend.rag.crawler import WebsiteCrawler
from backend.rag.embeddings import EmbeddingService
from backend.rag.vector import VectorService
from backend.rag.tasks.celery_app import get_celery_app


EXPORT_BASE_DIR = Path(__file__).resolve().parents[2] / "static" / "crawls"

celery_app = get_celery_app()


@celery_app.task(name="rag.crawl_website")
def crawl_website_task(website_id: str) -> dict:
    """Background task to crawl a website and store pages.

    Args:
        website_id: UUID of the website to crawl

    Returns:
        Dict with crawl results
    """
    return asyncio.run(_crawl_website_async(website_id))


def run_crawl_inline(website_id: str) -> dict:
    """Execute a crawl synchronously within the API process."""

    return asyncio.run(_crawl_website_async(website_id, use_celery_embeddings=False))


async def _crawl_website_async(
    website_id: str, *, use_celery_embeddings: bool | None = None
) -> dict:
    """Async implementation of website crawl."""
    session = SessionLocal()

    try:
        settings = get_settings()
        if use_celery_embeddings is None:
            use_celery_embeddings = (
                settings.rag_task_execution_mode == "celery"
            )

        # Fetch website
        result = session.execute(
            select(Website).where(Website.id == uuid.UUID(website_id))
        )
        website = result.scalar_one_or_none()

        if not website:
            return {"success": False, "error": "Website not found"}

        # Update status to crawling
        website.status = WebsiteStatus.CRAWLING
        session.commit()

        # Initialize crawler
        crawler = WebsiteCrawler(
            base_url=website.url,
            max_pages=website.max_pages,
        )

        # Crawl website
        pages = await crawler.crawl()

        # Store pages in database
        pages_created = 0
        pages_updated = 0

        for page_data in pages:
            # Check if page exists
            result = session.execute(
                select(WebsitePage).where(
                    WebsitePage.website_id == website.id,
                    WebsitePage.url == page_data["url"]
                )
            )
            existing_page = result.scalar_one_or_none()

            if existing_page:
                # Update if content changed
                if existing_page.content_hash != page_data["content_hash"]:
                    existing_page.content = page_data["content"]
                    existing_page.title = page_data["title"]
                    existing_page.page_metadata = page_data["metadata"]
                    existing_page.content_hash = page_data["content_hash"]
                    existing_page.last_crawled_at = datetime.utcnow()
                    pages_updated += 1

                    # Trigger embedding update
                    if use_celery_embeddings:
                        process_page_embeddings_task.delay(str(existing_page.id))
                    else:
                        await _process_page_embeddings_async(str(existing_page.id))
            else:
                # Create new page
                new_page = WebsitePage(
                    website_id=website.id,
                    url=page_data["url"],
                    title=page_data["title"],
                    content=page_data["content"],
                    page_metadata=page_data["metadata"],
                    content_hash=page_data["content_hash"],
                    last_crawled_at=datetime.utcnow(),
                )
                session.add(new_page)
                session.flush()
                pages_created += 1

                # Trigger embedding generation
                if use_celery_embeddings:
                    process_page_embeddings_task.delay(str(new_page.id))
                else:
                    await _process_page_embeddings_async(str(new_page.id))

        total_pages = session.execute(
            select(func.count()).select_from(WebsitePage).where(WebsitePage.website_id == website.id)
        ).scalar_one()

        # Update website status
        website.status = WebsiteStatus.READY
        website.last_crawled_at = datetime.utcnow()
        website.pages_indexed = total_pages
        website.crawl_error = None

        session.commit()

        export_path = _write_crawl_export_snapshot(
            website=website,
            pages=session.execute(
                select(WebsitePage)
                .where(WebsitePage.website_id == website.id)
                .order_by(WebsitePage.last_crawled_at.desc())
            ).scalars().all(),
        )

        return {
            "success": True,
            "pages_created": pages_created,
            "pages_updated": pages_updated,
            "total_pages": len(pages),
            "export_file": export_path.name if export_path else None,
        }

    except Exception as e:
        # Update website status to error
        if website:
            website.status = WebsiteStatus.ERROR
            website.crawl_error = str(e)
            session.commit()

        return {"success": False, "error": str(e)}
    finally:
        session.close()


def _write_crawl_export_snapshot(
    *, website: Website, pages: list[WebsitePage]
) -> Path | None:
    """Persist the latest crawl results to a JSON export on disk."""

    EXPORT_BASE_DIR.mkdir(parents=True, exist_ok=True)
    website_dir = EXPORT_BASE_DIR / str(website.id)
    website_dir.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "website_id": str(website.id),
        "website_url": website.url,
        "website_name": website.name,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "page_count": len(pages),
        "pages": [
            {
                "id": str(page.id),
                "url": page.url,
                "title": page.title,
                "content": page.content,
                "metadata": page.page_metadata,
                "content_hash": page.content_hash,
                "word_count": len(page.content.split()),
                "last_crawled_at": _serialize_datetime(page.last_crawled_at),
                "created_at": _serialize_datetime(page.created_at),
                "updated_at": _serialize_datetime(page.updated_at),
            }
            for page in pages
        ],
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    export_path = website_dir / f"{timestamp}.json"
    latest_path = website_dir / "latest.json"

    try:
        with export_path.open("w", encoding="utf-8") as export_file:
            json.dump(snapshot, export_file, ensure_ascii=False, indent=2)

        temp_latest = latest_path.with_suffix(".tmp")
        with temp_latest.open("w", encoding="utf-8") as latest_file:
            json.dump(snapshot, latest_file, ensure_ascii=False, indent=2)

        temp_latest.replace(latest_path)
    except OSError:
        return None

    return export_path


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.astimezone(timezone.utc).isoformat()


def get_latest_export_path(website_id: uuid.UUID) -> Path | None:
    """Return the latest export file for a website if it exists."""

    website_dir = EXPORT_BASE_DIR / str(website_id)
    latest_path = website_dir / "latest.json"

    if latest_path.exists():
        return latest_path

    json_files = sorted(website_dir.glob("*.json"), reverse=True)
    for file_path in json_files:
        if file_path.is_file():
            return file_path

    return None


@celery_app.task(name="rag.process_page_embeddings")
def process_page_embeddings_task(page_id: str) -> dict:
    """Background task to generate and store embeddings for a page."""
    return asyncio.run(_process_page_embeddings_async(page_id))


async def _process_page_embeddings_async(page_id: str) -> dict:
    """Async implementation of embedding generation."""
    session = SessionLocal()

    try:
        # Fetch page
        result = session.execute(
            select(WebsitePage).where(WebsitePage.id == uuid.UUID(page_id))
        )
        page = result.scalar_one_or_none()

        if not page:
            return {"success": False, "error": "Page not found"}

        # Initialize services
        embedding_service = EmbeddingService()
        vector_service = VectorService()

        # Delete old embeddings if they exist
        if page.embedding_ids:
            old_ids = list(page.embedding_ids.values())
            vector_service.delete_by_ids(old_ids)

        # Generate embeddings
        chunk_data = await embedding_service.embed_page(
            content=page.content,
            page_id=str(page.id),
            website_id=str(page.website_id),
            page_url=page.url,
        )

        # Store in vector DB
        embeddings = [chunk["embedding"] for chunk in chunk_data]
        metadata = [chunk["metadata"] for chunk in chunk_data]

        vector_ids = vector_service.upsert_embeddings(
            embeddings=embeddings,
            metadata=metadata,
        )

        # Update page with embedding IDs
        embedding_ids_map = {
            chunk["chunk_index"]: vector_id
            for chunk, vector_id in zip(chunk_data, vector_ids)
        }
        page.embedding_ids = embedding_ids_map

        session.commit()

        return {
            "success": True,
            "chunks_processed": len(chunk_data),
            "vector_ids": vector_ids,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        session.close()


__all__ = [
    "crawl_website_task",
    "process_page_embeddings_task",
    "run_crawl_inline",
    "get_latest_export_path",
]
