"""Celery tasks for website crawling and embedding generation."""

import asyncio
from datetime import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.rag.models.website import Website, WebsiteStatus
from backend.rag.models.website_page import WebsitePage
from backend.rag.crawler import WebsiteCrawler
from backend.rag.embeddings import EmbeddingService
from backend.rag.vector import VectorService
from backend.rag.tasks.celery_app import get_celery_app

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


async def _crawl_website_async(website_id: str) -> dict:
    """Async implementation of website crawl."""
    session = SessionLocal()

    try:
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
                    process_page_embeddings_task.delay(str(existing_page.id))
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
                process_page_embeddings_task.delay(str(new_page.id))

        # Update website status
        website.status = WebsiteStatus.READY
        website.last_crawled_at = datetime.utcnow()
        website.pages_indexed = pages_created + pages_updated
        website.crawl_error = None

        session.commit()

        return {
            "success": True,
            "pages_created": pages_created,
            "pages_updated": pages_updated,
            "total_pages": len(pages),
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


__all__ = ["crawl_website_task", "process_page_embeddings_task"]
