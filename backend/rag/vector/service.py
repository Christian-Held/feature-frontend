"""Vector database service for managing embeddings and similarity search."""

import uuid
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

from backend.rag.vector.client import get_qdrant_client, ensure_collection


class VectorService:
    """Service for managing vector embeddings in Qdrant."""

    def __init__(self, collection_name: str = "website_pages"):
        """Initialize the vector service.

        Args:
            collection_name: Name of the Qdrant collection to use
        """
        self.collection_name = collection_name
        self.client: QdrantClient = get_qdrant_client()
        ensure_collection(self.client, self.collection_name)

    def upsert_embeddings(
        self,
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Store or update embeddings with metadata.

        Args:
            embeddings: List of embedding vectors
            metadata: List of metadata dicts (must match embeddings length)
            ids: Optional list of vector IDs (will generate UUIDs if not provided)

        Returns:
            List of vector IDs that were upserted
        """
        if len(embeddings) != len(metadata):
            raise ValueError("Embeddings and metadata lists must have the same length")

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(embeddings))]

        # Create points
        points = [
            models.PointStruct(
                id=point_id,
                vector=embedding,
                payload=meta,
            )
            for point_id, embedding, meta in zip(ids, embeddings, metadata)
        ]

        # Upsert to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        return ids

    def search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        filter_conditions: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors.

        Args:
            query_embedding: The query vector
            limit: Maximum number of results to return
            filter_conditions: Optional filter dict (e.g., {"website_id": "123"})
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of search results with score and payload
        """
        # Build filter if provided
        query_filter = None
        if filter_conditions:
            must_conditions = [
                models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=value)
                )
                for key, value in filter_conditions.items()
            ]
            query_filter = models.Filter(must=must_conditions)

        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            query_filter=query_filter,
            score_threshold=score_threshold,
        )

        # Format results
        return [
            {
                "id": result.id,
                "score": result.score,
                "payload": result.payload,
            }
            for result in results
        ]

    def delete_by_website(self, website_id: str) -> None:
        """Delete all vectors for a specific website.

        Args:
            website_id: The website ID to filter by
        """
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="website_id",
                            match=models.MatchValue(value=website_id)
                        )
                    ]
                )
            ),
        )

    def delete_by_page(self, page_id: str) -> None:
        """Delete all vectors for a specific page.

        Args:
            page_id: The page ID to filter by
        """
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="page_id",
                            match=models.MatchValue(value=page_id)
                        )
                    ]
                )
            ),
        )

    def delete_by_ids(self, ids: List[str]) -> None:
        """Delete vectors by their IDs.

        Args:
            ids: List of vector IDs to delete
        """
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(points=ids),
        )

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection.

        Returns:
            Dict with collection stats (count, config, etc.)
        """
        info = self.client.get_collection(collection_name=self.collection_name)
        return {
            "name": self.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status,
        }
