"""
FAISS-based similarity search for product images.
"""

import numpy as np
import pickle
import logging
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import os

try:
    import faiss  # type: ignore
    _HAS_FAISS = True
except ImportError:  # pragma: no cover - optional heavy dep
    faiss = None  # type: ignore
    _HAS_FAISS = False

from config import settings

logger = logging.getLogger(__name__)


class SimilaritySearch:
    """FAISS-based similarity search for product image embeddings."""

    def __init__(self, embedding_dim: int = 2048):
        """
        Initialize the similarity search index.

        Args:
            embedding_dim: Dimension of the embedding vectors
        """
        self.embedding_dim = embedding_dim
        self.index = None
        self.product_ids: List[str] = []
        self.index_path = settings.FAISS_INDEX_PATH
        self.product_ids_path = settings.FAISS_PRODUCT_IDS_PATH
        self.is_built = False

    def build_index(self, embeddings: np.ndarray, product_ids: List[str]):
        """
        Build FAISS index from embeddings.

        Args:
            embeddings: numpy array of shape (n_products, embedding_dim)
            product_ids: List of product ID strings corresponding to each embedding
        """
        if len(embeddings) == 0 or len(embeddings) != len(product_ids):
            logger.error("Embeddings and product_ids length mismatch or empty")
            return

        # Ensure embeddings are float32
        embeddings = np.array(embeddings).astype(np.float32)

        # Create FAISS index (using Inner Product for cosine similarity with normalized vectors)
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.index.add(embeddings)
        self.product_ids = product_ids
        self.is_built = True

        logger.info(f"FAISS index built with {len(embeddings)} embeddings")

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Search for similar products.

        Args:
            query_embedding: Query feature vector
            top_k: Number of results to return

        Returns:
            List of (product_id, similarity_score) tuples, sorted by score descending
        """
        if self.index is None or not self.is_built:
            logger.warning("Index not built yet")
            return []

        query = np.array(query_embedding).astype(np.float32).reshape(1, -1)

        # Normalize query
        faiss.normalize_L2(query)

        scores, indices = self.index.search(query, min(top_k, self.index.ntotal))

        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < len(self.product_ids) and idx != -1:
                results.append((self.product_ids[idx], float(score)))

        return results

    def add_embedding(self, product_id: str, embedding: np.ndarray):
        """
        Add a single embedding to the index (requires rebuild for FAISS IndexFlat).

        Args:
            product_id: Product ID
            embedding: Feature vector

        Note: For production, consider IndexFlatIP with IDList for dynamic updates.
        """
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.product_ids = []

        embedding = np.array(embedding).astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(embedding)
        self.index.add(embedding)
        self.product_ids.append(product_id)
        self.is_built = True

    def remove_embedding(self, product_id: str) -> bool:
        """
        Remove an embedding from the index.

        Note: This requires rebuilding the index without the target product.

        Args:
            product_id: Product ID to remove

        Returns:
            True if removed, False if not found
        """
        if product_id not in self.product_ids:
            return False

        idx = self.product_ids.index(product_id)
        # FAISS IndexFlat doesn't support direct removal; rebuild is required
        remaining_ids = [pid for i, pid in enumerate(self.product_ids) if i != idx]

        # Get remaining embeddings (need to be stored separately for rebuild)
        logger.warning("Removal requires index rebuild - implement with stored embeddings")
        return False

    def save_index(self):
        """Save the FAISS index and product IDs to disk."""
        try:
            Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, self.index_path)
            with open(self.product_ids_path, 'wb') as f:
                pickle.dump(self.product_ids, f)
            logger.info("FAISS index saved successfully")
        except Exception as e:
            logger.error(f"Error saving index: {e}")

    def load_index(self) -> bool:
        """
        Load the FAISS index and product IDs from disk.

        Returns:
            True if loaded successfully
        """
        try:
            if not Path(self.index_path).exists() or not Path(self.product_ids_path).exists():
                logger.warning("FAISS index files not found")
                return False

            self.index = faiss.read_index(self.index_path)
            with open(self.product_ids_path, 'rb') as f:
                self.product_ids = pickle.load(f)
            self.is_built = True
            logger.info(f"FAISS index loaded with {len(self.product_ids)} products")
            return True
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            return False

    def get_stats(self) -> Dict:
        """Get index statistics."""
        return {
            'total_vectors': self.index.ntotal if self.index else 0,
            'embedding_dim': self.embedding_dim,
            'is_built': self.is_built,
            'num_products': len(self.product_ids)
        }
