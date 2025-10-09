"""RAG query service for answering questions using retrieval + generation."""

from typing import List, Dict, Any, Optional
import json

from openai import AsyncOpenAI

from backend.core.config import get_settings
from backend.rag.embeddings import EmbeddingService
from backend.rag.vector import VectorService

settings = get_settings()


class RAGQueryService:
    """Service for answering questions using RAG (Retrieval Augmented Generation)."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        max_context_chunks: int = 5,
        temperature: float = 0.7,
    ):
        """Initialize the RAG query service.

        Args:
            model: OpenAI chat model to use
            max_context_chunks: Maximum number of context chunks to retrieve
            temperature: LLM temperature for generation
        """
        self.model = model
        self.max_context_chunks = max_context_chunks
        self.temperature = temperature

        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.embedding_service = EmbeddingService()
        self.vector_service = VectorService()

    async def answer_question(
        self,
        question: str,
        website_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_qas: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Answer a question using RAG.

        Args:
            question: User's question
            website_id: Website ID to search within
            conversation_history: Previous messages in the conversation
            custom_qas: Custom Q&A pairs to check first

        Returns:
            Dict with answer, sources, and metadata
        """
        # 1. Check custom Q&As first (exact/fuzzy match)
        if custom_qas:
            for qa in custom_qas:
                # Simple keyword matching
                question_lower = question.lower()
                qa_question_lower = qa["question"].lower()

                # Check if question contains all words from custom Q&A
                qa_words = set(qa_question_lower.split())
                question_words = set(question_lower.split())

                if qa_words.issubset(question_words) or qa_question_lower in question_lower:
                    return {
                        "answer": qa["answer"],
                        "sources": [],
                        "type": "custom_qa",
                        "confidence": "high",
                    }

        # 2. Generate embedding for the question
        question_embedding = await self.embedding_service.generate_embedding(question)

        # 3. Search vector database
        search_results = self.vector_service.search(
            query_embedding=question_embedding,
            limit=self.max_context_chunks,
            filter_conditions={"website_id": website_id},
            score_threshold=0.5,  # Only include results with >50% similarity
        )

        if not search_results:
            return {
                "answer": "I couldn't find any relevant information to answer your question. Could you rephrase it or ask something else?",
                "sources": [],
                "type": "no_context",
                "confidence": "none",
            }

        # 4. Build context from search results
        context_parts = []
        sources = []

        for i, result in enumerate(search_results):
            context_parts.append(f"Context {i+1}:\n{result['payload']['text']}\n")
            sources.append({
                "page_url": result["payload"]["page_url"],
                "score": result["score"],
                "chunk_index": result["payload"]["chunk_index"],
            })

        context = "\n".join(context_parts)

        # 5. Build conversation messages
        messages = [
            {
                "role": "system",
                "content": """You are a helpful website assistant. Answer questions based ONLY on the provided context.
If the context doesn't contain enough information to answer the question, say so clearly.
Be concise, accurate, and helpful. Use a friendly, conversational tone.

When appropriate, you can suggest actions like:
- SHOW_MAP: If the user asks about location/address
- OPEN_HOURS: If the user asks about opening hours
- CONTACT_INFO: If the user asks about contact information
- HIGHLIGHT: If you want to highlight specific information on the page

Format actions as JSON at the end of your response like this:
ACTIONS: {"action": "SHOW_MAP", "data": {...}}
"""
            }
        ]

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add current question with context
        messages.append({
            "role": "user",
            "content": f"""Context information:
{context}

Question: {question}

Please answer the question based on the context provided above."""
        })

        # 6. Call OpenAI for generation
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=500,
        )

        answer = response.choices[0].message.content

        # 7. Parse actions if present
        actions = None
        if "ACTIONS:" in answer:
            parts = answer.split("ACTIONS:")
            answer = parts[0].strip()
            try:
                actions = json.loads(parts[1].strip())
            except:
                pass  # Ignore malformed actions

        # 8. Calculate confidence based on search scores
        avg_score = sum(r["score"] for r in search_results) / len(search_results)
        confidence = "high" if avg_score > 0.8 else "medium" if avg_score > 0.6 else "low"

        return {
            "answer": answer,
            "sources": sources,
            "type": "rag",
            "confidence": confidence,
            "actions": actions,
            "tokens_used": response.usage.total_tokens,
        }

    async def get_suggested_questions(
        self,
        website_id: str,
        limit: int = 5,
    ) -> List[str]:
        """Generate suggested questions based on website content.

        Args:
            website_id: Website ID
            limit: Number of suggestions to generate

        Returns:
            List of suggested questions
        """
        # Get collection info to check if there's content
        info = self.vector_service.get_collection_info()

        if info["points_count"] == 0:
            return [
                "What can you help me with?",
                "Tell me about this website.",
            ]

        # Use OpenAI to generate contextual suggestions
        # This is a simplified version - you could enhance this with actual content sampling
        return [
            "What are your opening hours?",
            "How can I contact you?",
            "Where are you located?",
            "What services do you offer?",
            "Do you have any special offers?",
        ]
