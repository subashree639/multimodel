"""
RAG (Retrieval-Augmented Generation) pipeline for the shopping assistant.
"""

import logging
from typing import List, Dict, Optional
import re

from nlp.sentiment_analysis import SentimentAnalyzer
from chatbot.vector_store import VectorStore
from database.schema import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline for product Q&A."""

    def __init__(self, vector_store: VectorStore, sentiment_analyzer: SentimentAnalyzer):
        """
        Initialize RAG pipeline.

        Args:
            vector_store: Vector store for product/review retrieval
            sentiment_analyzer: Sentiment analysis model
        """
        self.vector_store = vector_store
        self.sentiment_analyzer = sentiment_analyzer
        self.greeting_patterns = [
            r'\b(hi|hello|hey|good morning|good evening|howdy)\b',
            r'\b(thanks|thank you|thx)\b',
            r'\b(bye|goodbye|see you|exit|quit)\b',
        ]

    def is_greeting(self, message: str) -> Optional[str]:
        """Check if message is a greeting and return response type."""
        for pattern in self.greeting_patterns:
            if re.search(pattern, message.lower()):
                return 'greeting'
        if re.search(r'\b(bye|goodbye|see you)\b', message.lower()):
            return 'farewell'
        return None

    def retrieve_context(self, query: str, top_k: int = 5) -> Dict:
        """
        Retrieve relevant context for the query.

        Args:
            query: User query string
            top_k: Number of documents to retrieve

        Returns:
            Dictionary with retrieved products, reviews, and context text
        """
        products = self.vector_store.search_products(query, top_k=top_k)
        reviews = self.vector_store.search_reviews(query, top_k=top_k)

        context_parts = []
        relevant_products = []

        for doc in products:
            meta = doc.get('metadata', {})
            relevant_products.append({
                'product_id': str(meta.get('_id', '')),
                'name': meta.get('name', ''),
                'category': meta.get('category', ''),
                'price': meta.get('price', 0.0),
                'rating': meta.get('avg_rating', 0.0),
                'similarity': round(doc['similarity_score'], 3)
            })
            context_parts.append(
                f"Product: {meta.get('name', '')} | "
                f"Category: {meta.get('category', '')} | "
                f"Price: ${meta.get('price', 0.0)} | "
                f"Rating: {meta.get('avg_rating', 0.0)}/5 | "
                f"{meta.get('description', '')}"
            )

        for doc in reviews:
            context_parts.append(
                f"Customer Review ({doc['metadata'].get('rating', 0)}/5): "
                f"{doc['metadata'].get('text', '')}"
            )

        return {
            'products': relevant_products[:5],
            'reviews': [r['metadata'] for r in reviews[:3]],
            'context': '\n'.join(context_parts[:8])
        }

    def generate_response(self, query: str, context: Dict, user_id: str) -> str:
        """
        Generate a response based on retrieved context.
        (Uses heuristic generation; replace with LLM for advanced responses)

        Args:
            query: Original user query
            context: Retrieved context dictionary
            user_id: User identifier

        Returns:
            Generated response string
        """
        query_lower = query.lower()

        # Check for greetings
        greeting = self.is_greeting(query)
        if greeting == 'greeting':
            return "Hello! I'm your shopping assistant. How can I help you find the perfect product today?"
        if greeting == 'farewell':
            return "Goodbye! Feel free to come back anytime you need shopping help."

        # Context-aware responses
        if not context['products']:
            return "I couldn't find any specific products matching your query. Could you try rephrasing or provide more details about what you're looking for?"

        products = context['products']
        context_text = context['context']
        response = ""

        # Detect question type
        if any(word in query_lower for word in ['price', 'cost', 'expensive', 'cheap', 'budget', '$']):
            price_responses = []
            for p in products[:3]:
                price_responses.append(f"{p['name']} at ${p['price']:.2f}")
            response = f"Here are some price options:\n" + "\n".join(f"- {r}" for r in price_responses) + "\n\nWould you like more details on any of these?"

        elif any(word in query_lower for word in ['rating', 'best', 'top', 'recommended', 'review', 'popular']):
            best = sorted(products, key=lambda x: x.get('rating', 0), reverse=True)[0]
            response = f"Based on ratings, I recommend: {best['name']} with a rating of {best['rating']}/5 in the {best['category']} category. " \
            f"It's priced at ${best['price']:.2f}."

        elif any(word in query_lower for word in ['recommend', 'suggest', 'looking for', 'find', 'search']):
            rec_list = "\n".join(
                f"{i+1}. {p['name']} (${p['price']:.2f}, Rating: {p['rating']}/5)"
                for i, p in enumerate(products[:3])
            )
            response = f"Based on your query, here are my top recommendations:\n{rec_list}\n\nWould you like more information about any of these?"

        elif any(word in query_lower for word in ['compare', 'difference', 'vs', 'versus']):
            if len(products) >= 2:
                p1, p2 = products[0], products[1]
                response = (
                    f"Comparing {p1['name']} and {p2['name']}:\n"
                    f"- {p1['name']}: ${p1['price']:.2f}, Rating: {p1['rating']}/5\n"
                    f"- {p2['name']}: ${p2['price']:.2f}, Rating: {p2['rating']}/5\n"
                    f"\nBoth are in the {p1['category']} category. Would you like more details?"
                )
            else:
                rec_list = "\n".join(
                    f"{i+1}. {p['name']} (${p['price']:.2f}, Rating: {p['rating']}/5)"
                    for i, p in enumerate(products[:3])
                )
                response = f"I found some products that might interest you:\n{rec_list}\n\nHow can I help you further?"
        else:
            # Default response
            rec_list = "\n".join(
                f"{i+1}. {p['name']} (${p['price']:.2f}, Rating: {p['rating']}/5)"
                for i, p in enumerate(products[:3])
            )
            response = f"I found some products that might interest you:\n{rec_list}\n\nHow can I help you further?"

        return response
