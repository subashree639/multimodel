"""Admin endpoints: analytics, segmentation and dashboard stats.

Every route except ``/health`` requires an authenticated admin user.
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user, require_admin
from api.serializers import serialize_doc
from database.mongodb import db_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
def health():
    """Unauthenticated liveness probe for the admin service."""
    return {"status": "ok"}


@router.get("/sales-analytics")
async def sales_analytics(_: Dict[str, Any] = Depends(require_admin)):
    """Return sales analytics computed from real collections."""
    db = db_manager.get_async_db()

    total_products = await db.products.count_documents({})
    total_users = await db.users.count_documents({})
    total_reviews = await db.reviews.count_documents({})
    total_orders = await db.orders.count_documents({})

    total_revenue = 0.0
    async for doc in db.orders.aggregate([{"$group": {"_id": None, "total": {"$sum": "$total"}}}]):
        total_revenue = float(doc.get("total", 0) or 0)

    # Best selling products: aggregate actual ordered quantities.
    best_sellers = []
    async for doc in db.orders.aggregate([
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.product_id",
            "sold": {"$sum": "$items.quantity"},
            "revenue": {"$sum": "$items.subtotal"},
        }},
        {"$sort": {"sold": -1}},
        {"$limit": 10},
    ]):
        product = await db.products.find_one({"_id": _try_oid(doc["_id"])})
        if not product:
            continue
        best_sellers.append({
            "id": str(product["_id"]),
            "name": product.get("name", ""),
            "category": product.get("category", ""),
            "sales": int(doc.get("sold", 0)),
            "revenue": round(float(doc.get("revenue", 0) or 0), 2),
            "rating": product.get("avg_rating", 0),
            "price": product.get("price", 0),
        })

    trending = []
    cursor = db.products.find({"is_trending": True}).limit(10)
    async for p in cursor:
        trending.append({
            "id": str(p["_id"]),
            "name": p.get("name", ""),
            "category": p.get("category", ""),
            "rating": p.get("avg_rating", 0),
            "price": p.get("price", 0),
        })

    categories = []
    async for doc in db.products.aggregate(
        [{"$group": {"_id": "$category", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
    ):
        if doc["_id"]:
            categories.append({"category": doc["_id"], "count": doc["count"]})

    sentiment_dist: Dict[str, int] = {}
    async for doc in db.reviews.aggregate(
        [{"$group": {"_id": "$sentiment", "count": {"$sum": 1}}}]
    ):
        sentiment_dist[doc["_id"] or "neutral"] = doc["count"]

    # Real monthly revenue/order series derived from order timestamps.
    monthly: Dict[str, Dict[str, float]] = {}
    async for order in db.orders.find({}, {"total": 1, "created_at": 1}):
        created = order.get("created_at")
        if not created:
            continue
        key = f"{created.year}-{created.month:02d}"
        bucket = monthly.setdefault(key, {"revenue": 0.0, "orders": 0})
        bucket["revenue"] += float(order.get("total", 0) or 0)
        bucket["orders"] += 1

    if monthly:
        keys = sorted(monthly)[-12:]
    else:
        keys = []
    chart_data = {
        "labels": keys,
        "revenue": [round(monthly[k]["revenue"], 2) for k in keys],
        "orders": [int(monthly[k]["orders"]) for k in keys],
    }

    return {
        "totalRevenue": round(total_revenue, 2),
        "totalOrders": total_orders,
        "totalCustomers": total_users,
        "totalProducts": total_products,
        "totalReviews": total_reviews,
        "bestSellingProducts": best_sellers,
        "trendingProducts": trending,
        "categoryDistribution": categories,
        "sentimentDistribution": sentiment_dist,
        "chartData": chart_data,
    }


@router.get("/customer-segments")
async def customer_segments(_: Dict[str, Any] = Depends(require_admin)):
    """Return customer segmentation counts."""
    db = db_manager.get_async_db()
    segments = []
    async for doc in db.users.aggregate([
        {"$group": {"_id": "$preferences.segment", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]):
        segments.append({"segment": doc["_id"] or "General Buyer", "count": doc["count"]})
    return {"segments": segments}


@router.get("/dashboard-stats/{user_id}")
async def dashboard_stats(user_id: str, current: Dict[str, Any] = Depends(get_current_user)):
    """Per-user dashboard statistics (real counts from the database)."""
    if user_id not in (current["user_id"], "me", "current") and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="You may only read your own dashboard")

    db = db_manager.get_async_db()
    uid = current["user_id"]

    total_orders = await db.orders.count_documents({"user_id": uid})
    total_spent = 0.0
    async for doc in db.orders.aggregate([
        {"$match": {"user_id": uid}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}},
    ]):
        total_spent = float(doc.get("total", 0) or 0)

    wishlist_items = await db.wishlist.count_documents({"user_id": uid})
    cart_items = await db.cart.count_documents({"user_id": uid})
    my_reviews = await db.reviews.count_documents({"user_id": uid})

    user = await db.users.find_one({"_id": _try_oid(uid)})
    segment = (user or {}).get("preferences", {}).get("segment", "General Buyer")

    recent = []
    cursor = db.user_behavior.find({"user_id": uid}).sort("timestamp", -1).limit(10)
    async for b in cursor:
        recent.append({
            "action": b.get("action", ""),
            "product_id": b.get("product_id", ""),
            "timestamp": b.get("timestamp"),
        })

    return {
        "segment": segment,
        "totalOrders": total_orders,
        "totalSpent": round(total_spent, 2),
        "wishlistItems": wishlist_items,
        "cartItems": cart_items,
        "myReviews": my_reviews,
        "recentActivity": recent,
    }


@router.post("/run-analytics")
async def run_analytics(_: Dict[str, Any] = Depends(require_admin)):
    """Re-run sales trend analysis and customer segmentation off-loop."""
    messages = []
    try:
        from training.sales_analytics import SalesAnalyzer

        analyzer = SalesAnalyzer()
        await asyncio.to_thread(analyzer.update_database_trends)
        messages.append("sales trends updated")
    except Exception as e:
        logger.error("Sales analytics error: %s", e)
        messages.append(f"sales analytics failed: {e}")

    try:
        from nlp.customer_segmentation import CustomerSegmenter

        segmenter = CustomerSegmenter()
        await asyncio.to_thread(segmenter.update_database_segments)
        messages.append("customer segments updated")
    except Exception as e:
        logger.error("Customer segmentation error: %s", e)
        messages.append(f"segmentation failed: {e}")

    return {"message": "Analytics pipeline executed", "details": messages}


@router.post("/load-data")
async def load_data(_: Dict[str, Any] = Depends(require_admin)):
    """Placeholder: data ingestion is an offline script."""
    return {"message": "Data loading endpoint - use training/ingest_to_mongodb.py"}


def _try_oid(value: str):
    from bson import ObjectId
    from bson.errors import InvalidId

    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None
