"""Collaborative filtering with TruncatedSVD matrix factorization."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

DEFAULT_RATING = 3.0


class CollaborativeFilteringRecommender:
    """User-item collaborative filtering via latent-factor SVD."""

    def __init__(self, n_components: int = 50):
        self.n_components = n_components
        self.svd: Optional[TruncatedSVD] = None
        self.user_factors = None
        self.item_factors = None
        self.user_id_map: Dict[str, int] = {}
        self.product_id_map: Dict[str, int] = {}
        self.reverse_user_map: Dict[int, str] = {}
        self.reverse_product_map: Dict[int, str] = {}
        self.ratings_matrix: Optional[csr_matrix] = None
        self.is_fitted = False
        self.user_ratings: Dict[str, Dict[str, float]] = {}
        self.pred_min: float = 0.0
        self.pred_max: float = 1.0

    def _reset(self) -> None:
        """Clear all fitted state so a refit cannot leak stale id maps."""
        self.user_id_map = {}
        self.product_id_map = {}
        self.reverse_user_map = {}
        self.reverse_product_map = {}
        self.user_ratings = {}
        self.is_fitted = False

    @staticmethod
    def _iter_valid_reviews(reviews: List[Dict]):
        """Yield (user_id, product_id, rating), averaging duplicate pairs."""
        seen: Dict[Tuple[str, str], List[float]] = {}
        order: List[Tuple[str, str]] = []
        for review in reviews or []:
            user_id = review.get("user_id")
            product_id = review.get("product_id")
            if user_id is None or product_id is None:
                continue
            key = (str(user_id), str(product_id))
            if key not in seen:
                seen[key] = []
                order.append(key)
            try:
                rating = float(review.get("rating", DEFAULT_RATING))
            except (TypeError, ValueError):
                rating = DEFAULT_RATING
            seen[key].append(rating)

        for key in order:
            values = seen[key]
            yield key[0], key[1], float(np.mean(values))

    def _build_ratings_matrix(self, reviews: List[Dict]) -> csr_matrix:
        """Build a sparse user x item matrix (duplicates averaged, not summed)."""
        rows, cols, data = [], [], []
        for user_id, product_id, rating in self._iter_valid_reviews(reviews):
            if user_id not in self.user_id_map:
                idx = len(self.user_id_map)
                self.user_id_map[user_id] = idx
                self.reverse_user_map[idx] = user_id
            if product_id not in self.product_id_map:
                idx = len(self.product_id_map)
                self.product_id_map[product_id] = idx
                self.reverse_product_map[idx] = product_id

            rows.append(self.user_id_map[user_id])
            cols.append(self.product_id_map[product_id])
            data.append(rating)
            self.user_ratings.setdefault(user_id, {})[product_id] = rating

        shape = (len(self.user_id_map), len(self.product_id_map))
        if not data:
            return csr_matrix(shape)
        return csr_matrix((data, (rows, cols)), shape=shape)

    def fit(self, reviews: List[Dict], products: List[Dict]) -> None:
        """Fit the SVD model. ``products`` is accepted for API symmetry."""
        logger.info(
            "Fitting collaborative filtering with %d reviews, %d products",
            len(reviews or []), len(products or []),
        )
        self._reset()
        self.ratings_matrix = self._build_ratings_matrix(reviews or [])

        if self.ratings_matrix.shape[0] < 2 or self.ratings_matrix.shape[1] < 2:
            logger.warning("Not enough data for collaborative filtering")
            return

        n_components = min(
            self.n_components,
            self.ratings_matrix.shape[0] - 1,
            self.ratings_matrix.shape[1] - 1,
        )
        if n_components < 1:
            return

        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        latent_matrix = self.svd.fit_transform(self.ratings_matrix)
        self.user_factors = latent_matrix
        self.item_factors = self.svd.components_.T

        # SVD output is not on a 5-star scale — record the observed prediction
        # range so scores can be mapped to [0, 1] honestly.
        all_preds = latent_matrix @ self.item_factors.T
        self.pred_min = float(np.min(all_preds))
        self.pred_max = float(np.max(all_preds))

        self.is_fitted = True
        logger.info(
            "Collaborative filtering fitted. Users: %d, Products: %d",
            len(self.user_id_map), len(self.product_id_map),
        )

    def predict_ratings(self, user_id: str) -> Dict[str, float]:
        """Return predicted raw scores for every known product of a user."""
        if not self.is_fitted or user_id not in self.user_id_map:
            return {}
        user_vector = self.user_factors[self.user_id_map[user_id]]
        preds = np.dot(user_vector, self.item_factors.T)
        return {
            self.reverse_product_map[i]: float(preds[i])
            for i in range(len(preds))
            if i in self.reverse_product_map
        }

    def normalize(self, raw_score: float) -> float:
        """Map a raw SVD prediction into [0, 1] using the observed range."""
        span = self.pred_max - self.pred_min
        if span <= 1e-9:
            return 0.5
        return float(min(1.0, max(0.0, (raw_score - self.pred_min) / span)))

    @staticmethod
    def _normalize_user(predictions: Dict[str, float]) -> Dict[str, float]:
        """Min-max normalise one user's own prediction distribution.

        Sparse SVD reconstructions are globally biased (the matrix is
        mean-centred over observed entries only), so a global min-max makes
        every user's best pick score ~0.3 while review sentiment sits at 0.9+.
        Normalising within the user's own candidate set keeps the collaborative
        weight (0.40) meaningful: their best match scores 1.0, their worst 0.0.
        """
        if not predictions:
            return {}
        values = np.array(list(predictions.values()), dtype=float)
        lo, hi = float(values.min()), float(values.max())
        span = hi - lo
        if span <= 1e-9:
            return {pid: 0.5 for pid in predictions}
        return {pid: float((value - lo) / span) for pid, value in predictions.items()}

    def get_recommendations(
        self,
        user_id: str,
        top_n: int = 10,
        exclude_history: Optional[List[str]] = None,
    ) -> List[Tuple[str, float, Dict]]:
        """Top-N collaborative recommendations for a known user."""
        if not self.is_fitted or user_id not in self.user_id_map:
            return []

        preds = self.predict_ratings(user_id)
        normalized = self._normalize_user(preds)
        exclude = set(str(pid) for pid in (self.user_ratings.get(user_id, {}).keys()))
        if exclude_history:
            exclude.update(str(pid) for pid in exclude_history)

        ranked = sorted(preds.items(), key=lambda kv: kv[1], reverse=True)
        recommendations: List[Tuple[str, float, Dict]] = []
        for product_id, raw in ranked:
            if len(recommendations) >= top_n:
                break
            if product_id in exclude:
                continue
            recommendations.append((
                product_id,
                normalized.get(product_id, 0.0),
                {
                    "reason": "Similar users liked this",
                    "predicted_rating": round(self.clamp_to_stars(raw), 2),
                    "algorithm": "collaborative_filtering",
                },
            ))
        return recommendations

    def clamp_to_stars(self, raw_score: float) -> float:
        """Interpret an SVD reconstruction as a 1-5 star estimate."""
        return float(min(5.0, max(1.0, raw_score)))

    def get_user_similarity(self, user_id: str, top_n: int = 10) -> List[Tuple[str, float]]:
        """Return the most similar users (cosine over latent factors)."""
        if not self.is_fitted or user_id not in self.user_id_map:
            return []
        user_idx = self.user_id_map[user_id]
        user_vector = self.user_factors[user_idx].reshape(1, -1)
        similarities = cosine_similarity(user_vector, self.user_factors)[0]

        similar: List[Tuple[str, float]] = []
        for idx in np.argsort(similarities)[::-1]:
            if len(similar) >= top_n:
                break
            if idx != user_idx:
                similar.append((self.reverse_user_map[int(idx)], float(similarities[idx])))
        return similar

    def update_user(self, user_id: str, product_id: str, rating: float) -> None:
        """Record a new rating in memory (full retraining needs a refit)."""
        self.user_ratings.setdefault(user_id, {})[product_id] = float(rating)
