"""
Visual product search: find visually similar products given an uploaded image.
"""

import logging
from typing import List, Tuple, Dict, Optional
import numpy as np

from .feature_extractor import ResNet50FeatureExtractor
from .similarity_search import SimilaritySearch

logger = logging.getLogger(__name__)


class VisualSearch:
    """Find visually similar products using image embeddings."""

    def __init__(self, device: Optional[str] = None):
        """
        Initialize visual search system.

        Args:
            device: Device for PyTorch operations
        """
        self.device = device
        self.feature_extractor = ResNet50FeatureExtractor(device=device)
        self.similarity_search = SimilaritySearch(
            embedding_dim=self.feature_extractor.get_feature_dimension()
        )
        self.products_index: Dict[str, Dict] = {}

    def index_products(self, products: List[Dict], embeddings: List[np.ndarray]):
        """
        Index products with their visual embeddings.

        Args:
            products: List of product dictionaries
            embeddings: Corresponding list of feature vectors
        """
        if len(products) != len(embeddings):
            raise ValueError("Products and embeddings count must match")

        valid_products = []
        valid_embeddings = []
        valid_ids = []

        for product, embedding in zip(products, embeddings):
            if embedding is not None:
                pid = str(product['_id'])
                valid_products.append(product)
                valid_embeddings.append(embedding)
                valid_ids.append(pid)
                self.products_index[pid] = product

        if not valid_embeddings:
            logger.warning("No valid embeddings to index")
            return

        self.similarity_search.build_index(
            embeddings=np.array(valid_embeddings),
            product_ids=valid_ids
        )

        logger.info(f"Indexed {len(valid_embeddings)} products for visual search")

    def search_by_image(
        self,
        image_path: str,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Search for similar products using an uploaded image.

        Args:
            image_path: Path to the query image
            top_k: Number of results to return

        Returns:
            List of product dictionaries with similarity scores
        """
        # Extract features from query image
        query_features = self.feature_extractor.extract_features(image_path)
        if query_features is None:
            logger.error("Failed to extract features from query image")
            return []

        # Search similar products
        results = self.similarity_search.search(query_features, top_k=top_k)

        # Build response with product details
        search_results = []
        for product_id, score in results:
            product_info = self.products_index.get(product_id, {})
            search_results.append({
                'product_id': product_id,
                'product': product_info,
                'similarity_score': round(float(score), 4),
                'match_percentage': round(float(score) * 100, 1)
            })

        return search_results

    def search_by_embedding(
        self,
        embedding: np.ndarray,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Search for similar products using a pre-computed embedding.

        Args:
            embedding: Feature vector
            top_k: Number of results to return

        Returns:
            List of product dictionaries with similarity scores
        """
        results = self.similarity_search.search(embedding, top_k=top_k)

        search_results = []
        for product_id, score in results:
            product_info = self.products_index.get(product_id, {})
            search_results.append({
                'product_id': product_id,
                'product': product_info,
                'similarity_score': round(float(score), 4),
                'match_percentage': round(float(score) * 100, 1)
            })

        return search_results

    def add_product_image(self, product_id: str, image_path: str) -> Optional[np.ndarray]:
        """
        Add a product's image to the index.

        Args:
            product_id: Product ID
            image_path: Path to product image

        Returns:
            Extracted embedding, or None on failure
        """
        embedding = self.feature_extractor.extract_features(image_path)
        if embedding is None:
            return None

        self.similarity_search.add_embedding(product_id, embedding)
        return embedding

    def save_index(self):
        """Save the FAISS index to disk."""
        self.similarity_search.save_index()

    def load_index(self) -> bool:
        """Load the FAISS index from disk."""
        return self.similarity_search.load_index()
