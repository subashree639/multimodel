"""Learning-to-Rank upgrade over the weighted hybrid baseline.

Pipeline: Multiple Candidate Generators -> Candidate Pool -> Feature
Engineering -> LTR model (sklearn GradientBoosting, no new deps) ->
Personalized Top-K. Evaluated against the baseline with the same
train/test split (see recommendation.evaluation).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

FEATURE_NAMES = ["collab", "content", "sentiment", "trend", "rating_norm", "pop_norm"]


def _product_stats(products: List[Dict]) -> Tuple[Dict[str, Dict], float]:
    index = {str(p["_id"]): p for p in products if p.get("_id") is not None}
    vols = [float(p.get("num_reviews") or 0) for p in index.values()]
    vmax = max(vols) if vols else 1.0
    return index, vmax or 1.0


def build_features(
    pid: str,
    product_index: Dict[str, Dict],
    vmax: float,
    collab: float,
    content: float,
    sentiment: float,
    trend: float,
) -> List[float]:
    p = product_index.get(pid, {})
    rating_norm = float(p.get("avg_rating") or 0) / 5.0
    pop_norm = min(float(p.get("num_reviews") or 0) / vmax, 1.0)
    return [collab, content, sentiment, trend, rating_norm, pop_norm]


class LearningToRank:
    """Pointwise ranker trained on (features -> relevance) from train reviews."""

    def __init__(self):
        from sklearn.ensemble import GradientBoostingRegressor

        self.model = GradientBoostingRegressor(random_state=42)
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        if len(X) == 0:
            logger.warning("LTR fit called with no rows")
            return
        self.model.fit(X, y)
        self.is_fitted = True
        logger.info(f"LTR fitted on {len(X)} rows, {X.shape[1]} features")

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            return np.zeros(len(X))
        return self.model.predict(X)


def train_ltr_from_hybrid(hybrid, products: List[Dict], train_reviews: List[Dict]) -> LearningToRank:
    """Create pointwise training rows from the hybrid's own candidate pool.

    For each train user: candidates = hybrid candidates; label = 1 if the
    candidate is a train-relevant item (rating>=4) else 0. This keeps the LTR
    aligned with the same signals while learning better weights.
    """
    product_index, vmax = _product_stats(products)
    # Per-user relevant sets from train.
    rel: Dict[str, set] = {}
    for r in train_reviews:
        try:
            if float(r.get("rating", 0)) >= 4.0:
                rel.setdefault(str(r.get("user_id")), set()).add(str(r.get("product_id")))
        except (TypeError, ValueError):
            continue

    X_rows, y_rows = [], []
    for user, rel_items in list(rel.items())[:200]:
        # Candidate pool: union of collab/content/popular (via hybrid internals).
        hist: List[str] = []
        collab_recs = hybrid.collaborative_recommender.get_recommendations(user, top_n=30)
        content_recs = hybrid.content_recommender.get_recommendations({}, hist, top_n=30)
        pool: Dict[str, Tuple[float, float]] = {}
        for pid, s, _ in collab_recs:
            pool[str(pid)] = (hybrid.collaborative_recommender.normalize(s), pool.get(str(pid), (0, 0))[1])
        for pid, s, _ in content_recs:
            prev = pool.get(str(pid), (0, 0))
            pool[str(pid)] = (prev[0], max(0.0, min(1.0, float(s))))
        if len(pool) < 5:
            for pid in hybrid.popular_product_ids[:30]:
                pool.setdefault(pid, (0.0, 0.0))
        for pid, (cb, ct) in pool.items():
            st = hybrid.product_sentiments.get(pid, 0.5)
            tr = hybrid.product_trend_scores.get(pid, 0.0)
            X_rows.append(build_features(pid, product_index, vmax, cb, ct, st, tr))
            y_rows.append(1.0 if pid in rel_items else 0.0)

    ltr = LearningToRank()
    if X_rows:
        ltr.fit(np.asarray(X_rows, dtype=float), np.asarray(y_rows, dtype=float))
    return ltr


def rerank_with_ltr(hybrid, ltr: LearningToRank, user_id: str, top_n: int = 10,
                    user_preferences=None, user_history=None) -> List[Tuple[str, float, Dict]]:
    """Generate hybrid candidates then re-score with the LTR model."""
    base = hybrid.get_recommendations(user_id, user_preferences, user_history, top_n=top_n * 3)
    if not base or not ltr.is_fitted:
        return base[:top_n]
    product_index, vmax = _product_stats(hybrid.products)
    X = []
    for pid, _, exp in base:
        sig = exp.get("signals", {})
        X.append(build_features(pid, product_index, vmax, sig.get("collaborative", 0),
                                sig.get("content", 0), sig.get("sentiment", 0.5), sig.get("trend", 0)))
    scores = ltr.predict(np.asarray(X, dtype=float))
    order = sorted(zip(base, scores), key=lambda t: float(t[1]), reverse=True)
    out = []
    for (pid, _, exp), s in order[:top_n]:
        exp = dict(exp)
        exp["ltr_score"] = round(float(s), 4)
        out.append((pid, float(s), exp))
    return out
