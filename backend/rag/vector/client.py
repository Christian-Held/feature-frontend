"""Qdrant vector database client configuration."""

from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models
from backend.core.config import get_settings

settings = get_settings()


@lru_cache()
def get_qdrant_client() -> QdrantClient:
    """Get or create a singleton Qdrant client instance.

    Returns:
        QdrantClient: Configured Qdrant client
    """
    # For local development, use in-memory mode
    # For production, connect to Qdrant server
    if settings.qdrant_url:
        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=30,
        )
    else:
        # In-memory client for development/testing
        client = QdrantClient(location=":memory:")

    return client


def ensure_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int = 1536,  # OpenAI text-embedding-3-small dimension
) -> None:
    """Ensure a collection exists with the correct configuration.

    Args:
        client: Qdrant client instance
        collection_name: Name of the collection to create/verify
        vector_size: Dimension of the embedding vectors (default: 1536 for OpenAI)
    """
    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [col.name for col in collections]

    if collection_name not in collection_names:
        # Create collection with cosine similarity
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )
