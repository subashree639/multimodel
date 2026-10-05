"""Wishlist endpoints (auth-protected, IDOR-safe)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_current_user
from api.serializers import serialize_product
from database.mongodb import db_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class WishlistAddRequest(BaseModel):
    product_id: str
    user_id: Optional[str] = Field(
        default=None,
        description="Optional; must match the authenticated user when supplied.",
    )


def _assert_owner(user_id: str, current: Dict[str, Any]) -> None:
    if user_id not in (current["user_id"], "me", "current") and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="You may only access your own wishlist")


@router.get("/{user_id}")
async def get_wishlist(user_id: str, current: Dict[str, Any] = Depends(get_current_user)):
    """Get the authenticated user's wishlist with product details."""
    _assert_owner(user_id, current)
    db = db_manager.get_async_db()
    items = []

    cursor = db.wishlist.find({"user_id": current["user_id"]})
    async for item in cursor:
        try:
            product = await db.products.find_one({"_id": ObjectId(item.get("product_id", ""))})
        except (InvalidId, TypeError):
            logger.warning("Wishlist row has invalid product_id=%r", item.get("product_id"))
            continue
        if product:
            items.append({
                "product": serialize_product(product),
                "added_at": item.get("created_at"),
            })

    return {"user_id": current["user_id"], "items": items}


@router.post("/add")
async def add_to_wishlist(req: WishlistAddRequest, current: Dict[str, Any] = Depends(get_current_user)):
    """Add a product to the wishlist (idempotent)."""
    if req.user_id and req.user_id not in (current["user_id"], "me", "current") and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="You may only modify your own wishlist")

    db = db_manager.get_async_db()
    try:
        ObjectId(req.product_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Product not found")

    product = await db.products.find_one({"_id": ObjectId(req.product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    user_id = current["user_id"]
    existing = await db.wishlist.find_one({"user_id": user_id, "product_id": req.product_id})
    if existing:
        return {"message": "Already in wishlist", "already_exists": True}

    await db.wishlist.insert_one({
        "user_id": user_id,
        "product_id": req.product_id,
        "created_at": datetime.now(timezone.utc),
    })
    try:
        await db.user_behavior.insert_one({
            "user_id": user_id,
            "product_id": req.product_id,
            "action": "wishlist",
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception as e:
        logger.debug("user_behavior write failed: %s", e)

    return {"message": "Added to wishlist", "already_exists": False}


@router.delete("/remove/{user_id}/{product_id}")
async def remove_from_wishlist(
    user_id: str, product_id: str, current: Dict[str, Any] = Depends(get_current_user)
):
    """Remove a product from the wishlist."""
    _assert_owner(user_id, current)
    db = db_manager.get_async_db()
    result = await db.wishlist.delete_one(
        {"user_id": current["user_id"], "product_id": product_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not in wishlist")
    return {"message": "Removed from wishlist"}
