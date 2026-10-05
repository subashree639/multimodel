"""Offline evaluation for the hybrid recommender — no data leakage.

Splits each user's rated items into train/test by time-agnostic random holdout
(reviews carry no timestamps, so we hold out N items per user), fits the
recommender on train only, and scores ranked lists against held-out items.

Metrics: Precision@K, Recall@K, NDCG@K, Hit Rate@K, MAP@K.
"""

from __future__ import annotations

import logging
import math
import random
from collections import defaultdict
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def _relevant_items(reviews: List[Dict], min_rating: float = 4.0) -> Dict[str, set]:
    rel: Dict[str, set] = defaultdict(set)
    for r in reviews:
        try:
            if float(r.get("rating", 0)) >= min_rating:
                rel[str(r.get("user_id"))].add(str(r.get("product_id")))
        except (TypeError, ValueError):
            continue
    return rel


def train_test_split(
    reviews: List[Dict], n_holdout: int = 2, seed: int = 42, min_rating: float = 4.0
) -> Tuple[List[Dict], Dict[str, set]]:
    """Hold out up to n_holdout relevant items per user; return (train, test_rel)."""
    rng = random.Random(seed)
    rel = _relevant_items(reviews, min_rating)
    holdout: Dict[str, set] = {}
    for u, items in rel.items():
        items = list(items)
        if len(items) < 2:
            continue  # need at least 1 train + 1 test
        k = min(n_holdout, len(items) - 1)
        holdout[u] = set(rng.sample(items, k))
    holdout_pairs = {(u, p) for u, ps in holdout.items() for p in ps}
    train = [r for r in reviews if (str(r.get("user_id")), str(r.get("product_id"))) not in holdout_pairs]
    return train, holdout


def precision_at_k(ranked: List[str], relevant: set, k: int) -> float:
    if k <= 0 or not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / k


def recall_at_k(ranked: List[str], relevant: set, k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def hit_rate_at_k(ranked: List[str], relevant: set, k: int) -> float:
    if not relevant:
        return 0.0
    return 1.0 if set(ranked[:k]) & relevant else 0.0


def ndcg_at_k(ranked: List[str], relevant: set, k: int) -> float:
    dcg = sum(1.0 / math.log2(i + 2) for i, pid in enumerate(ranked[:k]) if pid in relevant)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    return dcg / ideal if ideal > 0 else 0.0


def average_precision_at_k(ranked: List[str], relevant: set, k: int) -> float:
    if not relevant:
        return 0.0
    hits, total = 0, 0.0
    for i, pid in enumerate(ranked[:k], 1):
        if pid in relevant:
            hits += 1
            total += hits / i
    return total / min(len(relevant), k)


def evaluate(
    recommender,
    products: List[Dict],
    train_reviews: List[Dict],
    test_rel: Dict[str, set],
    k: int = 10,
    max_users: int = 50,
) -> Dict[str, float]:
    """Fit recommender on train and score on held-out relevants.

    Uses only train for fitting (no leakage); history passed to
    get_recommendations is also train-only.
    """
    from recommendation.hybrid_recommender import HybridRecommender

    rec: HybridRecommender = recommender
    trending: List[str] = []
    rec.fit(products, train_reviews, trending)

    # Train history per user (train-only item ids).
    train_hist: Dict[str, List[str]] = defaultdict(list)
    for r in train_reviews:
        train_hist[str(r.get("user_id"))].append(str(r.get("product_id")))

    users = [u for u in test_rel if u in train_hist][:max_users]
    if not users:
        return {"users": 0, "precision@k": 0.0, "recall@k": 0.0, "ndcg@k": 0.0, "hit_rate@k": 0.0, "map@k": 0.0}

    agg = {"p": 0.0, "r": 0.0, "n": 0.0, "h": 0.0, "m": 0.0}
    for u in users:
        ranked = [pid for pid, _, _ in rec.get_recommendations(u, {}, train_hist[u], top_n=k)]
        rel = test_rel[u]
        agg["p"] += precision_at_k(ranked, rel, k)
        agg["r"] += recall_at_k(ranked, rel, k)
        agg["n"] += ndcg_at_k(ranked, rel, k)
        agg["h"] += hit_rate_at_k(ranked, rel, k)
        agg["m"] += average_precision_at_k(ranked, rel, k)
    n = len(users)
    return {
        "users": n,
        "k": k,
        "precision@k": round(agg["p"] / n, 4),
        "recall@k": round(agg["r"] / n, 4),
        "ndcg@k": round(agg["n"] / n, 4),
        "hit_rate@k": round(agg["h"] / n, 4),
        "map@k": round(agg["m"] / n, 4),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from database.mongodb import db_manager

    db = db_manager.get_sync_db()
    products = list(db.products.find({}))
    reviews = list(db.reviews.find({}))
    train, test = train_test_split(reviews)
    from recommendation.hybrid_recommender import HybridRecommender

    print(evaluate(HybridRecommender(), products, train, test, k=10))
