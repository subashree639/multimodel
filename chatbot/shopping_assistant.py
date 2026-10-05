"""
Shopping assistant chatbot with RAG capabilities.
"""

import logging
from typing import List, Dict, Optional
from chatbot.vector_store import VectorStore
from chatbot.rag_pipeline import RAGPipeline
from nlp.sentiment_analysis import SentimentAnalyzer
from database.schema import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class ShoppingAssistant:
    """AI shopping assistant chatbot with RAG."""

    def __init__(self, vector_store: VectorStore, sentiment_analyzer: SentimentAnalyzer):
        self.vector_store = vector_store
        self.sentiment_analyzer = sentiment_analyzer
        self.rag_pipeline = RAGPipeline(vector_store, sentiment_analyzer)
        self.conversation_history: Dict[str, List[Dict]] = {}

    def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message and return a response.

        Args:
            request: Chat request with user_id and message

        Returns:
            Chat response with answer and relevant products
        """
        user_id = request.user_id
        message = request.message.strip()

        if not message:
            return ChatResponse(
                response="Please enter a message.",
                relevant_products=[],
                sources=[]
            )

        # Store in conversation history
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append({'role': 'user', 'content': message})

        # Retrieve context
        context = self.rag_pipeline.retrieve_context(message, top_k=5)

        # Generate response
        response_text = self.rag_pipeline.generate_response(message, context, user_id)
        response_text += "\n\nNeed more help? Just ask!"

        # Store assistant response
        self.conversation_history[user_id].append({'role': 'assistant', 'content': response_text})

        # Build sources list
        sources = []
        for p in context['products'][:3]:
            sources.append(f"Product: {p['name']} (ID: {p['product_id']})")
        for r in context['reviews'][:2]:
            review_id = r.get('_id', r.get('product_id', ''))
            sources.append(f"Review on product {review_id}")

        return ChatResponse(
            response=response_text,
            relevant_products=context['products'][:5],
            sources=sources
        )

    def get_conversation_history(self, user_id: str) -> List[Dict]:
        """Get conversation history for a user."""
        return self.conversation_history.get(user_id, [])

    def clear_history(self, user_id: str):
        """Clear conversation history for a user."""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
