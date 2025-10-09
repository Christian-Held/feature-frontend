"""Embedding generation service using OpenAI."""

from typing import List, Dict, Any

import tiktoken
from openai import AsyncOpenAI

from backend.core.config import get_settings

settings = get_settings()


class EmbeddingService:
    """Service for generating embeddings and chunking text."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ):
        """Initialize the embedding service.

        Args:
            model: OpenAI embedding model to use
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Number of tokens to overlap between chunks
        """
        self.model = model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Get encoding for token counting
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base for newer models
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks based on token count.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        # Encode text to tokens
        tokens = self.encoding.encode(text)

        chunks = []
        start = 0

        while start < len(tokens):
            # Get chunk
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]

            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)

            # Move start position with overlap
            start = end - self.chunk_overlap

        return chunks

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # OpenAI API supports batch embedding
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
        )

        # Sort by index to maintain order
        embeddings = sorted(response.data, key=lambda x: x.index)
        return [emb.embedding for emb in embeddings]

    async def embed_page(
        self,
        content: str,
        page_id: str,
        website_id: str,
        page_url: str,
    ) -> List[Dict[str, Any]]:
        """Chunk and embed a page's content.

        Args:
            content: Page content to embed
            page_id: Database ID of the page
            website_id: Database ID of the website
            page_url: URL of the page

        Returns:
            List of dicts with chunk text, embedding, and metadata
        """
        # Split into chunks
        chunks = self.chunk_text(content)

        # Generate embeddings for all chunks
        embeddings = await self.generate_embeddings(chunks)

        # Combine with metadata
        results = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            results.append({
                "chunk_index": i,
                "text": chunk,
                "embedding": embedding,
                "metadata": {
                    "page_id": page_id,
                    "website_id": website_id,
                    "page_url": page_url,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }
            })

        return results

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))
