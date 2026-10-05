"""
Vector store for RAG (Retrieval-Augmented Generation) pipeline.
"""

import logging
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# config must come first: it sets USE_TF=0, without which the transformers TF
# stubs raise on import in this Keras 3 environment.
from config import settings

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    _HAS_SENTENCE_TRANSFORMERS = True
except Exception:  # pragma: no cover - optional heavy dep (ImportError *or* env issues)
    SentenceTransformer = None  # type: ignore
    _HAS_SENTENCE_TRANSFORMERS = False

logger = logging.getLogger(__name__)


class VectorStore:
    """Vector store for semantic search over product catalog and reviews."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", index_path: str = None):
        """
        Initialize vector store.

        Args:
            model_name: Sentence transformer model name
            index_path: Path to save/load the index
        """
        self.model_name = model_name
        self.index_path = index_path or "models/vector_store.pkl"
        self.model = None
        self.documents: List[Dict] = []
        self.embeddings: np.ndarray = None
        self._load_model()

    def _load_model(self):
        """Load the sentence transformer model."""
        if not _HAS_SENTENCE_TRANSFORMERS:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Install it with: pip install sentence-transformers"
            )
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded sentence transformer: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def add_documents(self, documents: List[Dict]):
        """
        Add documents to the vector store.

        Args:
            documents: List of dicts with 'text', 'product_id', 'type' fields
        """
        texts = [doc['text'] for doc in documents]

        # Generate embeddings
        if self.embeddings is None:
            self.embeddings = self.model.encode(texts, show_progress_bar=True)
        else:
            new_embeddings = self.model.encode(texts, show_progress_bar=True)
            self.embeddings = np.vstack([self.embeddings, new_embeddings])

        self.documents.extend(documents)
        logger.info(f"Added {len(documents)} documents. Total: {len(self.documents)}")

    def add_products(self, products: List[Dict]):
        """
        Index products for retrieval.

        Args:
            products: List of product dictionaries
        """
        documents = []
        for product in products:
            pid = str(product['_id'])
            doc_text = (
                f"Product: {product.get('name', '')}. "
                f"Category: {product.get('category', '')}. "
                f"Description: {product.get('description', '')}. "
                f"Features: {', '.join(product.get('features', []))}. "
                f"Price: ${product.get('price', 0)}. "
                f"Rating: {product.get('avg_rating', 0)}/5."
            )
            documents.append({
                'text': doc_text,
                'product_id': pid,
                'type': 'product',
                'metadata': product
            })

        self.add_documents(documents)

    def add_reviews(self, reviews: List[Dict]):
        """
        Index product reviews for retrieval.

        Args:
            reviews: List of review dictionaries
        """
        documents = []
        for review in reviews:
            doc_text = (
                f"Review: {review.get('text', '')}. "
                f"Rating: {review.get('rating', 0)}/5. "
                f"Sentiment: {review.get('sentiment', 'neutral')}."
            )
            documents.append({
                'text': doc_text,
                'product_id': str(review.get('product_id', '')),
                'type': 'review',
                'metadata': review
            })

        self.add_documents(documents)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for relevant documents.

        Args:
            query: Search query text
            top_k: Number of results to return
            filter_type: Optional filter for document type

        Returns:
            List of matching documents with similarity scores
        """
        if self.embeddings is None or len(self.documents) == 0:
            logger.warning("Vector store is empty")
            return []

        # Encode query
        query_embedding = self.model.encode([query])

        # Compute cosine similarity
        similarities = np.dot(self.embeddings, query_embedding.T).flatten()

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            doc = self.documents[idx].copy()
            doc['similarity_score'] = float(similarities[idx])
            if filter_type and doc.get('type') != filter_type:
                continue
            results.append(doc)

        return results

    def search_products(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search specifically for products."""
        return self.search(query, top_k=top_k, filter_type='product')

    def search_reviews(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search specifically for reviews."""
        return self.search(query, top_k=top_k, filter_type='review')

    def get_document_count(self) -> int:
        """Return the number of indexed documents."""
        return len(self.documents)

    def save(self):
        """Save the vector store to disk."""
        try:
            Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
            data = {
                'documents': self.documents,
                'embeddings': self.embeddings,
                'model_name': self.model_name
            }
            with open(self.index_path, 'wb') as f:
                pickle.dump(data, f)
            logger.info("Vector store saved successfully")
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")

    def load(self) -> bool:
        """
        Load vector store from disk.

        Returns:
            True if loaded successfully
        """
        try:
            if not Path(self.index_path).exists():
                return False

            with open(self.index_path, 'rb') as f:
                data = pickle.load(f)

            self.documents = data['documents']
            self.embeddings = data['embeddings']
            self.model_name = data['model_name']

            if self.model is None or self.model.get_sentence_embedding_dimension() != self.embeddings.shape[1]:
                self._load_model()

            logger.info(f"Vector store loaded. Documents: {len(self.documents)}")
            return True

        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            return False
