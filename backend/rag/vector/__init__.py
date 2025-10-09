"""Vector database client and services for RAG embeddings."""

from backend.rag.vector.client import get_qdrant_client
from backend.rag.vector.service import VectorService

__all__ = ["get_qdrant_client", "VectorService"]
