"""Celery tasks for RAG crawling and embedding."""

from backend.rag.tasks.crawl import crawl_website_task, process_page_embeddings_task

__all__ = ["crawl_website_task", "process_page_embeddings_task"]
