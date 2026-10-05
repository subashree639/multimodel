"""Hybrid recommender: candidate generation + weighted fusion + explanations.

Baseline scoring (weights from ``config.py`` — do not change casually)::

    score = 0.40 * SVD_collaborative
          + 0.25 * content_similarity
          + 0.20 * review_sentiment
          + 0.15 * sales_trend

Candidate sources are the collaborative model, the content model and — for
cold start / sparse candidates — a popularity-trend fallback, so the engine
never returns an empty list while the catalogue is non-empty.

Every result carries a structured explanation::

    {
      "reasons": ["Matches your preferred category", ...],
      "signals": {"collaborative": 0.91, "content": 0.84, ...},
      "sources": ["collaborative_filtering", ...],
      ...
    }
"""

from __future__ import annotations

import logging
from statistics import median
from typing import Dict, Iterable, List, Optional, Tuple

from config import settings
from recommendation.collaborative_filtering import CollaborativeFilteringRecommender
from recommendation.content_based import ContentBasedRecommender

logger = logging.getLogger(__name__)

Recommendation = Tuple[str, float, Dict]


def _min_max(scores: Dict[str, float], floor: float = 0.0) -> Dict[str, float]:
    """Rescale a dict of scores so its maximum maps to 1.0.

    Constant inputs (all equal, empty span) are returned as ``floor`` — a flat
    signal must not be presented as a perfect match.
    """
    if not scores:
        return {}
    values = list(scores.values())
    lo, hi = min(values), max(values)
    span = hi - lo
    if span <= 1e-9:
        return {pid: floor for pid in scores}
    return {pid: float((v - lo) / span) for pid, v in scores.items()}


class HybridRecommender:
    """Weighted fusion of collaborative, content, sentiment and trend signals."""

    def __init__(
        self,
        svd_weight: Optional[float] = None,
        similarity_weight: Optional[float] = None,
        sentiment_weight: Optional[float] = None,
        sales_trend_weight: Optional[float] = None,
    ):
        # `or` would treat an explicit 0.0 as "unset" — use None checks.
        self.svd_weight = (
            settings.COLLABORATIVE_FILTER_WEIGHT if svd_weight is None else svd_weight
        )
        self.similarity_weight = (
            settings.CONTENT_BASED_WEIGHT if similarity_weight is None else similarity_weight
        )
        self.sentiment_weight = (
            settings.SENTIMENT_WEIGHT if sentiment_weight is None else sentiment_weight
        )
        self.sales_trend_weight = (
            settings.SALES_TREND_WEIGHT if sales_trend_weight is None else sales_trend_weight
        )

        self.collaborative_recommender = CollaborativeFilteringRecommender()
        self.content_recommender = ContentBasedRecommender()

        self.is_fitted = False
        self.products: List[Dict] = []
        self.product_index: Dict[str, Dict] = {}
        self.product_sentiments: Dict[str, float] = {}
        self.product_trend_scores: Dict[str, float] = {}
        self.trending_product_ids: set = set()
        self.popular_product_ids: List[str] = []

    # ------------------------------------------------------------------ fit
    def fit(
        self,
        products: List[Dict],
        reviews: List[Dict],
        trending_ids: Optional[Iterable[str]] = None,
    ) -> None:
        """Fit all sub-models. Safe to call repeatedly (state is reset)."""
        self.is_fitted = False
        self.products = list(products or [])
        self.product_index = {}
        self.product_sentiments = {}
        self.product_trend_scores = {}
        self.trending_product_ids = set()
        self.popular_product_ids = []

        if not self.products:
            logger.warning("HybridRecommender.fit called with no products")
            return

        for p in self.products:
            pid = p.get("_id")
            if pid is None:
                continue
            self.product_index[str(pid)] = p

        if not self.product_index:
            logger.warning("No usable products (all missing _id)")
            return

        self._build_sentiment_from_reviews(reviews or [])
        self._build_trend_scores(self.products)

        # Explicit trending ids from the DB win over the heuristic score.
        for tid in trending_ids or []:
            self.trending_product_ids.add(str(tid))
            self.product_trend_scores[str(tid)] = max(
                1.0, self.product_trend_scores.get(str(tid), 0.0)
            )

        self.collaborative_recommender.fit(reviews or [], self.products)
        self.content_recommender.fit(self.products)

        # Popularity order powers the cold-start fallback.
        self.popular_product_ids = [
            str(p["_id"])
            for p in sorted(
                self.product_index.values(),
                key=lambda x: (
                    float(x.get("avg_rating") or 0) * 0.6
                    + min(float(x.get("num_reviews") or 0), 5000) / 5000.0
                ),
                reverse=True,
            )
        ]

        self.is_fitted = True
        logger.info(
            "HybridRecommender fitted: %d products, %d sentiments, %d trending",
            len(self.product_index), len(self.product_sentiments), len(self.trending_product_ids),
        )

    # ------------------------------------------------------------- internals
    def _build_sentiment_from_reviews(self, reviews: List[Dict]) -> None:
        """Average positive-sentiment probability per product."""
        totals: Dict[str, List[float]] = {}
        for review in reviews:
            pid = review.get("product_id")
            if not pid:
                continue
            scores = review.get("sentiment_scores") or {}
            if "positive" in scores:
                totals.setdefault(str(pid), []).append(float(scores["positive"]))
        for pid, values in totals.items():
            self.product_sentiments[pid] = sum(values) / len(values)

    def _build_trend_scores(self, products: List[Dict]) -> None:
        """Normalised trend score in [0, 1] from rating and review volume."""
        if not products:
            return
        volumes = [float(p.get("num_reviews") or 0) for p in products]
        max_volume = max(volumes) or 1.0
        for p in products:
            pid = str(p.get("_id"))
            if pid == "None":
                continue
            rating = float(p.get("avg_rating") or 0)
            volume = float(p.get("num_reviews") or 0)
            score = (rating / 5.0) * 0.5 + (volume / max_volume) * 0.5
            self.product_trend_scores[pid] = max(0.0, min(1.0, score))

    # -------------------------------------------------------- recommendations
    def get_recommendations(
        self,
        user_id: str,
        user_preferences: Optional[Dict] = None,
        user_history: Optional[List[str]] = None,
        top_n: int = 10,
    ) -> List[Recommendation]:
        """Return top-N ``(product_id, score, explanation)`` tuples.

        Handles cold start: users without history (or unknown to the
        collaborative model) still receive popularity/trend-based results, and
        the list is topped up from the catalogue if candidate generation was
        sparse.
        """
        if not self.is_fitted:
            logger.warning("HybridRecommender not fitted")
            return []

        user_preferences = user_preferences or {}
        user_history = [str(h) for h in (user_history or [])]
        history_set = set(user_history)
        cold_start = not user_history

        # --- candidate generation -------------------------------------------
        collab_recs: List[Recommendation] = []
        if not cold_start:
            collab_recs = self.collaborative_recommender.get_recommendations(
                user_id, top_n=top_n * 3, exclude_history=user_history
            )

        content_recs = self.content_recommender.get_recommendations(
            user_preferences, user_history, top_n=top_n * 3
        )

        svd_scores: Dict[str, float] = {}
        similarity_scores: Dict[str, float] = {}
        all_candidates: List[str] = []
        seen: set = set()

        def _add(pid: str) -> None:
            if pid not in seen and pid in self.product_index and pid not in history_set:
                seen.add(pid)
                all_candidates.append(pid)

        for pid, score, _ in collab_recs:
            svd_scores[pid] = max(0.0, min(1.0, float(score)))
            _add(pid)
        for pid, score, _ in content_recs:
            similarity_scores[pid] = max(0.0, min(1.0, float(score)))
            _add(pid)

        # The four signals live on different scales (SVD reconstruction,
        # cosine similarity, calibrated sentiment probability, trend ratio).
        # Affinity signals are re-scaled over the candidate pool so the
        # configured weights actually mean what they say; raw values are kept
        # for the explanation.
        raw_svd = dict(svd_scores)
        raw_content = dict(similarity_scores)
        svd_scores = _min_max(svd_scores)
        similarity_scores = _min_max(similarity_scores)

        # Cold start / sparse candidates: seed with popular products so the
        # engine never returns an empty list.
        seeded = False
        if len(all_candidates) < top_n:
            for pid in self.popular_product_ids:
                if len(all_candidates) >= top_n * 3:
                    break
                if pid not in seen and pid not in history_set:
                    _add(pid)
                    seeded = True

        if not all_candidates:
            return []

        # --- scoring ---------------------------------------------------------
        typical_prices = self._typical_price_range(user_history)
        preferred_categories = set(
            str(c).lower() for c in (user_preferences.get("preferred_categories") or [])
        )

        scored: List[Recommendation] = []
        for pid in all_candidates:
            product = self.product_index[pid]
            svd_score = svd_scores.get(pid, 0.0)
            sim_score = similarity_scores.get(pid, 0.0)
            sentiment_available = pid in self.product_sentiments
            sentiment_score = self.product_sentiments.get(pid, 0.5)
            trend_score = self.product_trend_scores.get(pid, 0.0)

            final_score = (
                self.svd_weight * svd_score
                + self.similarity_weight * sim_score
                + self.sentiment_weight * sentiment_score
                + self.sales_trend_weight * trend_score
            )

            explanation = self._explain(
                product=product,
                pid=pid,
                svd_score=svd_score,
                sim_score=sim_score,
                sentiment_score=sentiment_score,
                sentiment_available=sentiment_available,
                trend_score=trend_score,
                user_preferences=user_preferences,
                preferred_categories=preferred_categories,
                typical_prices=typical_prices,
                cold_start=cold_start,
                seeded=seeded,
            )
            explanation["raw_signals"] = {
                "collaborative": round(raw_svd.get(pid, 0.0), 4),
                "content": round(raw_content.get(pid, 0.0), 4),
            }
            explanation["scored_with"] = (
                "baseline weights over per-candidate normalised affinity signals"
            )
            scored.append((pid, min(final_score, 1.0), explanation))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_n]

    def _typical_price_range(self, user_history: List[str]) -> Optional[Tuple[float, float]]:
        """(low, high) price band of the user's known history, if any."""
        prices = [
            float(self.product_index[pid].get("price") or 0)
            for pid in user_history
            if pid in self.product_index and float(self.product_index[pid].get("price") or 0) > 0
        ]
        if not prices:
            return None
        mid = median(prices)
        return (mid * 0.5, mid * 1.5)

    def _explain(
        self,
        *,
        product: Dict,
        pid: str,
        svd_score: float,
        sim_score: float,
        sentiment_score: float,
        sentiment_available: bool,
        trend_score: float,
        user_preferences: Dict,
        preferred_categories: set,
        typical_prices: Optional[Tuple[float, float]],
        cold_start: bool,
        seeded: bool,
    ) -> Dict:
        """Build a structured, signal-backed explanation.

        Only reasons that are actually supported by a signal are emitted.
        """
        reasons: List[str] = []
        sources: List[str] = []

        category = str(product.get("category") or "").lower()

        if svd_score > 0.35:
            sources.append("collaborative_filtering")
            reasons.append("Similar users with comparable taste liked this product")
        if sim_score > 0.15:
            sources.append("content_based")
            reasons.append("Similar to products you have viewed or purchased")
        if sentiment_available and sentiment_score > 0.6:
            sources.append("positive_sentiment")
            reasons.append("Reviews for this product are strongly positive")
        if pid in self.trending_product_ids or trend_score > 0.3:
            sources.append("sales_trend")
            reasons.append("Trending based on recent sales and ratings")

        if preferred_categories and category in preferred_categories:
            reasons.append("Matches your preferred category")

        avg_rating = float(product.get("avg_rating") or 0)
        num_reviews = float(product.get("num_reviews") or 0)
        if avg_rating >= 4.3 and num_reviews >= 50:
            reasons.append(f"Highly rated ({avg_rating:.1f}/5 from {int(num_reviews)} ratings)")

        price = float(product.get("price") or 0)
        if typical_prices and price > 0:
            low, high = typical_prices
            if low <= price <= high:
                reasons.append("Within your typical price range")

        if cold_start:
            if pid in self.trending_product_ids:
                reasons.append("Popular this week — showing trending picks for a new profile")
            elif seeded:
                reasons.append("New profile — showing popular, well-rated products")
            else:
                reasons.append("No interaction history yet — showing widely liked products")

        if not reasons:
            reasons.append("Selected by the hybrid ranking model")

        return {
            "reason": " + ".join(sources) if sources else "popularity_fallback",
            "reasons": reasons,
            "signals": {
                "collaborative": round(svd_score, 4),
                "content": round(sim_score, 4),
                "sentiment": round(sentiment_score, 4),
                "trend": round(trend_score, 4),
            },
            "signal_presence": {
                "collaborative": svd_score > 0,
                "content": sim_score > 0,
                "sentiment": sentiment_available,
                "trend": trend_score > 0,
            },
            "sources": sources,
            "svd_score": round(svd_score, 4),
            "similarity_score": round(sim_score, 4),
            "sentiment_score": round(sentiment_score, 4),
            "sales_trend_score": round(trend_score, 4),
            "final_score": None,  # filled in by the caller
            "is_trending": pid in self.trending_product_ids,
            "cold_start": cold_start,
            "why_recommended": reasons,
        }

    # ------------------------------------------------------------ similarity
    def get_similar_products(self, product_id: str, top_n: int = 10) -> List[Tuple[str, float]]:
        """Content-similarity neighbours for one product."""
        if not self.is_fitted:
            return []
        return self.content_recommender.get_similar_products(product_id, top_n=top_n)

    def get_top_n(
        self,
        user_id: str,
        user_preferences: Optional[Dict] = None,
        user_history: Optional[List[str]] = None,
        top_n: int = 10,
    ) -> List[Recommendation]:
        """Backwards-compatible alias for :meth:`get_recommendations`."""
        return self.get_recommendations(
            user_id=user_id,
            user_preferences=user_preferences,
            user_history=user_history,
            top_n=top_n,
        )
