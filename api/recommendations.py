"""Recommendation endpoints: personalised feed, similar items, co-purchase."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_optional_user
from api.serializers import serialize_product
from database.mongodb import db_manager
from recommendation.hybrid_recommender import HybridRecommender

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory recommender instance (fit on demand, refit when data changes).
recommender = HybridRecommender()
_fit_lock = asyncio.Lock()
_fit_snapshot: Dict[str, int] = {"products": -1, "reviews": -1}


def _try_oid(value: Any) -> Optional[ObjectId]:
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return None


async def _ensure_fitted(db) -> None:
    """Fit (or refit) the recommender when the underlying counts change.

    Fitting is CPU-bound, so it runs in a worker thread; the lock prevents a
    stampede of concurrent requests each fitting their own copy.
    """
    product_count = await db.products.count_documents({})
    review_count = await db.reviews.count_documents({})

    if (
        recommender.is_fitted
        and _fit_snapshot["products"] == product_count
        and _fit_snapshot["reviews"] == review_count
    ):
        return

    async with _fit_lock:
        if (
            recommender.is_fitted
            and _fit_snapshot["products"] == product_count
            and _fit_snapshot["reviews"] == review_count
        ):
            return

        logger.info(
            "Fitting HybridRecommender (%d products, %d reviews)...",
            product_count, review_count,
        )
        # NB: the recommender needs name/description/category (content model),
        # price/rating/review counts (features + trend) and sentiment history.
        products = [p async for p in db.products.find({})]
        reviews = [r async for r in db.reviews.find({})]

        trending_ids = [
            str(p["_id"]) async for p in db.products.find(
                {"is_trending": True}, {"_id": 1}
            ).limit(25)
        ]
        if not trending_ids:
            trending_ids = [
                str(p["_id"]) async for p in db.products.find(
                    {}, {"_id": 1}
                ).sort([("avg_rating", -1), ("num_reviews", -1)]).limit(5)
            ]

        await asyncio.to_thread(recommender.fit, products, reviews, trending_ids)
        _fit_snapshot["products"] = product_count
        _fit_snapshot["reviews"] = review_count


async def _resolve_user(db, user_id: str, current: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Resolve a user document from an id, email, ``'me'`` or the JWT.

    Never raises 404 for an unknown identifier — an unknown/anonymous request
    falls back to a synthetic guest profile so cold-start recommendations are
    still returned.
    """
    if user_id in ("me", "current", "guest") and current:
        user_id = current["user_id"]

    query_candidates = []
    oid = _try_oid(user_id)
    if oid:
        query_candidates.append({"_id": oid})
    if "@" in user_id:
        query_candidates.append({"email": user_id.lower()})

    user: Optional[Dict[str, Any]] = None
    for query in query_candidates:
        user = await db.users.find_one(query)
        if user:
            break

    if user is None and current:
        user = await db.users.find_one({"_id": _try_oid(current["user_id"])})

    if user is None:
        logger.info("Recommendations requested for unknown user %r — cold start", user_id)
        return {
            "_id": None,
            "id": "guest",
            "preferences": {},
            "segment": "New Visitor",
        }

    user["id"] = str(user.get("_id") or "guest")
    return user


async def _user_history(db, user_id: str) -> List[str]:
    """Product ids the user has reviewed or purchased."""
    history: List[str] = []
    async for review in db.reviews.find({"user_id": user_id}, {"product_id": 1}):
        pid = review.get("product_id")
        if pid and pid not in history:
            history.append(pid)

    async for order in db.orders.find({"user_id": user_id}, {"items": 1}):
        for item in order.get("items", []):
            pid = item.get("product_id", "")
            if pid and pid not in history:
                history.append(pid)

    async for row in db.cart.find({"user_id": user_id}, {"product_id": 1}):
        pid = row.get("product_id")
        if pid and pid not in history:
            history.append(pid)
    return history


async def _trending_products(db, limit: int = 10) -> List[Dict]:
    cursor = db.products.find({"is_trending": True}).sort(
        "avg_rating", -1
    ).limit(limit)
    trending = [serialize_product(p) async for p in cursor]
    if trending:
        return trending

    cursor = db.products.find({}).sort([("avg_rating", -1), ("num_reviews", -1)]).limit(limit)
    return [serialize_product(p) async for p in cursor]


@router.get("/{user_id}")
async def get_recommendations(user_id: str, top_n: int = 10,
                              current: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    """Personalised recommendations. Cold start for unknown/guest users."""
    db = db_manager.get_async_db()
    await _ensure_fitted(db)

    user = await _resolve_user(db, user_id, current)
    actual_user_id = user.get("id") or "guest"
    preferences = user.get("preferences") or {}
    history = await _user_history(db, actual_user_id)

    rec_results = recommender.get_recommendations(
        user_id=actual_user_id,
        user_preferences=preferences,
        user_history=history,
        top_n=max(1, min(top_n, 50)),
    )

    recommendations: List[Dict[str, Any]] = []
    for pid, score, explanation in rec_results:
        prod = await db.products.find_one({"_id": _try_oid(pid)})
        if not prod:
            continue
        explanation = dict(explanation)
        explanation["final_score"] = round(score, 4)
        recommendations.append({
            "product": serialize_product(prod),
            "score": round(score, 4),
            "explanation": explanation,
        })

    trending = await _trending_products(db)

    # Defence in depth: the engine already seeds candidates, but if the
    # catalogue is filtered down to nothing we still honour the contract.
    if not recommendations and trending:
        recommendations = [
            {
                "product": p,
                "score": 0.5,
                "explanation": {
                    "reason": "popularity_fallback",
                    "reasons": ["Popular product — no personalised signals available"],
                    "signals": {"collaborative": 0, "content": 0, "sentiment": 0.5, "trend": 0.5},
                    "sources": ["popularity"],
                },
            }
            for p in trending[:top_n]
        ]

    return {
        "user_id": actual_user_id,
        "recommendations": recommendations,
        "trending": trending,
        "user_segment": preferences.get("segment", user.get("segment", "New Visitor")),
        "personalized": bool(history),
        "cold_start": not history,
    }


@router.get("/similar/{product_id}")
async def get_similar_products(product_id: str, limit: int = 5):
    """Content-similarity neighbours of one product."""
    db = db_manager.get_async_db()
    await _ensure_fitted(db)

    similar_pairs = recommender.get_similar_products(product_id, top_n=max(1, min(limit, 20)))

    results = []
    for pid, score in similar_pairs:
        prod = await db.products.find_one({"_id": _try_oid(pid)})
        if not prod:
            continue
        results.append({
            "product": serialize_product(prod),
            "similarity_score": round(score, 4),
        })

    return {"product_id": product_id, "similar_products": results}


@router.get("/frequently-bought-together/{product_id}")
async def frequently_bought_together(product_id: str, limit: int = 5):
    """Products ordered together (order co-occurrence, review fallback)."""
    db = db_manager.get_async_db()
    from collections import Counter

    co_products: Counter = Counter()
    async for order in db.orders.find({"items.product_id": product_id}, {"items": 1}):
        for item in order.get("items", []):
            pid = item.get("product_id", "")
            if pid and pid != product_id:
                co_products[pid] += 1

    if not co_products:
        user_ids = set()
        async for r in db.reviews.find({"product_id": product_id}, {"user_id": 1}):
            user_ids.add(r.get("user_id", ""))
        for uid in list(user_ids)[:20]:
            async for r in db.reviews.find({"user_id": uid}, {"product_id": 1}):
                pid = r.get("product_id", "")
                if pid and pid != product_id:
                    co_products[pid] += 1

    results = []
    for pid, count in co_products.most_common(max(1, min(limit, 20))):
        prod = await db.products.find_one({"_id": _try_oid(pid)})
        if not prod:
            continue
        results.append({
            "product": serialize_product(prod),
            "co_purchase_count": count,
        })

    return {"product_id": product_id, "frequently_bought_together": results}
