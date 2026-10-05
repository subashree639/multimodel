"""Legacy offline-RAG chatbot package (reference implementation).

NOTE: the production API path is :mod:`api.chat`, which answers directly
from live MongoDB product/review data (no model download, no hallucinated
catalogue entries). This package (ShoppingAssistant / VectorStore /
RAGPipeline over CSV snapshots + sentence-transformers) is kept as an
offline reference and is NOT used by the running server.
"""
from .rag_pipeline import RAGPipeline
from .vector_store import VectorStore
from .shopping_assistant import ShoppingAssistant

__all__ = ["RAGPipeline", "VectorStore", "ShoppingAssistant"]
