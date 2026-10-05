"""Product catalogue endpoints (list / search / detail / trending)."""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query

from api.serializers import serialize_product
from database.mongodb import db_manager

logger = logging.getLogger(__name__)
router = APIRouter()


def _as_object_id(product_id: str) -> ObjectId:
    """Convert a path parameter to ObjectId, raising a clean 404 on failure."""
    try:
        return ObjectId(product_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Product not found")


def _escape(value: str) -> str:
    """Escape user input before interpolating into a $regex filter."""
    return re.escape(value)


@router.get("/trending")
async def get_trending_products(limit: int = Query(10, ge=1, le=50)):
    """Return trending products (falls back to highest rated)."""
    db = db_manager.get_async_db()

    fallback = False
    cursor = db.products.find({"is_trending": True}).limit(limit)
    products = [p async for p in cursor]

    if not products:
        fallback = True
        cursor = db.products.find({}).sort(
            [("avg_rating", -1), ("num_reviews", -1)]
        ).limit(limit)
        products = [p async for p in cursor]

    return {
        "products": [serialize_product(p) for p in products],
        "total": len(products),
        "is_fallback": fallback,
    }


@router.get("/categories")
async def get_categories():
    """Return distinct product categories."""
    db = db_manager.get_async_db()
    try:
        categories = await db.products.distinct("category")
        categories = sorted(c for c in categories if c and str(c).strip())
        return {"categories": categories}
    except Exception as e:
        logger.error("Error fetching categories: %s", e)
        raise HTTPException(status_code=500, detail="Could not load categories")


@router.get("")
async def list_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    sort_by: str = "name",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List/search products with pagination."""
    db = db_manager.get_async_db()
    query: dict = {}

    if search and search.strip():
        query["name"] = {"$regex": _escape(search.strip()), "$options": "i"}
    if category and category.lower() != "all":
        query["category"] = {"$regex": f"^{_escape(category.strip())}$", "$options": "i"}
    if min_price is not None or max_price is not None:
        price_filter: dict = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        query["price"] = price_filter

    sort_opts = [("name", 1)]
    if sort_by == "price":
        sort_opts = [("price", 1)]
    elif sort_by == "price_desc":
        sort_opts = [("price", -1)]
    elif sort_by == "rating":
        sort_opts = [("avg_rating", -1)]
    elif sort_by == "popularity":
        sort_opts = [("num_reviews", -1)]

    skip = (page - 1) * limit
    total = await db.products.count_documents(query)
    cursor = db.products.find(query).sort(sort_opts).skip(skip).limit(limit)
    products = [serialize_product(p) async for p in cursor]

    return {
        "products": products,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/{product_id}")
async def get_product(product_id: str):
    """Single product with its review sentiment summary."""
    db = db_manager.get_async_db()
    doc = await db.products.find_one({"_id": _as_object_id(product_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")

    doc = serialize_product(doc)
    product_id_str = doc["id"]

    review_count = await db.reviews.count_documents({"product_id": product_id_str})
    cursor = db.reviews.find({"product_id": product_id_str}).sort(
        "created_at", -1
    ).limit(50)
    reviews = []
    async for r in cursor:
        r["id"] = str(r.pop("_id"))
        reviews.append(r)

    if reviews:
        n = len(reviews)
        sentiment = {
            "positive": round(
                sum(r.get("sentiment_scores", {}).get("positive", 0.0) for r in reviews) / n, 4
            ),
            "negative": round(
                sum(r.get("sentiment_scores", {}).get("negative", 0.0) for r in reviews) / n, 4
            ),
            "neutral": round(
                sum(r.get("sentiment_scores", {}).get("neutral", 0.0) for r in reviews) / n, 4
            ),
        }
    else:
        # No reviews yet — report zeros rather than a fabricated distribution.
        sentiment = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}

    from nlp.aspect_extraction import aggregate_aspect_profile

    doc["sentiment"] = sentiment
    doc["reviews"] = reviews[:10]
    doc["review_count"] = review_count
    doc["aspect_profile"] = aggregate_aspect_profile(reviews)
    return doc
