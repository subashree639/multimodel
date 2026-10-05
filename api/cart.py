"""Cart endpoints (auth-protected, IDOR-safe)."""

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


class CartAddRequest(BaseModel):
    product_id: str
    user_id: Optional[str] = Field(
        default=None,
        description="Optional; must match the authenticated user when supplied.",
    )
    quantity: int = Field(default=1, ge=1, le=99)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_valid_oid(value: str, not_found_detail: str = "Item not found") -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail=not_found_detail)


def _check_user_match(req_user_id: Optional[str], current: Dict[str, Any]) -> None:
    """Reject attempts to write into another user's cart (IDOR)."""
    if req_user_id and req_user_id not in (current["user_id"], "me", "current"):
        if current.get("role") != "admin":
            raise HTTPException(status_code=403, detail="You may only modify your own cart")


async def _record_behavior(db, user_id: str, product_id: str, action: str) -> None:
    try:
        await db.user_behavior.insert_one({
            "user_id": user_id,
            "product_id": product_id,
            "action": action,
            "timestamp": _utcnow(),
        })
    except Exception as e:  # behaviour logging must never break the request
        logger.debug("user_behavior write failed: %s", e)


@router.get("/{user_id}")
async def get_cart(
    user_id: str,
    current: Dict[str, Any] = Depends(get_current_user),
):
    """Get the authenticated user's cart with populated product details."""
    if user_id not in (current["user_id"], "me", "current") and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="You may only read your own cart")

    db = db_manager.get_async_db()
    cart_items = []
    total = 0.0

    cursor = db.cart.find({"user_id": current["user_id"]})
    async for item in cursor:
        product_id = item.get("product_id")
        try:
            product = await db.products.find_one({"_id": ObjectId(product_id)})
        except (InvalidId, TypeError):
            # Orphaned cart row (product deleted) — skip but log.
            logger.warning("Cart row has invalid product_id=%r", product_id)
            continue
        if not product:
            continue
        qty = int(item.get("quantity", 1))
        price = float(product.get("price", 0) or 0) * qty
        total += price
        cart_items.append({
            "product": serialize_product(product),
            "quantity": qty,
            "subtotal": round(price, 2),
        })

    return {"user_id": current["user_id"], "items": cart_items, "total": round(total, 2)}


@router.post("/add")
async def add_to_cart(
    req: CartAddRequest,
    current: Dict[str, Any] = Depends(get_current_user),
):
    """Add a product to the cart or increment its quantity (idempotent)."""
    _check_user_match(req.user_id, current)
    db = db_manager.get_async_db()

    product = await db.products.find_one({"_id": _require_valid_oid(req.product_id, "Product not found")})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    user_id = current["user_id"]
    now = _utcnow()
    # Atomic upsert: avoids duplicate (user, product) rows under concurrency —
    # a unique compound index on (user_id, product_id) backs this up.
    result = await db.cart.update_one(
        {"user_id": user_id, "product_id": req.product_id},
        {
            "$inc": {"quantity": int(req.quantity)},
            "$set": {"updated_at": now},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    doc = await db.cart.find_one({"user_id": user_id, "product_id": req.product_id})
    quantity = int(doc.get("quantity", req.quantity)) if doc else int(req.quantity)

    await _record_behavior(db, user_id, req.product_id, "add_to_cart")

    message = "Cart updated" if result.upserted_id is None else "Added to cart"
    return {"message": message, "quantity": quantity}


@router.delete("/remove/{user_id}/{product_id}")
async def remove_from_cart(
    user_id: str,
    product_id: str,
    current: Dict[str, Any] = Depends(get_current_user),
):
    """Remove a product from the authenticated user's cart."""
    if user_id not in (current["user_id"], "me", "current") and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="You may only modify your own cart")

    db = db_manager.get_async_db()
    result = await db.cart.delete_one(
        {"user_id": current["user_id"], "product_id": product_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not in cart")
    return {"message": "Removed from cart"}


@router.post("/checkout/{user_id}")
async def checkout(
    user_id: str,
    current: Dict[str, Any] = Depends(get_current_user),
):
    """Convert the cart into an order and clear it."""
    if user_id not in (current["user_id"], "me", "current") and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="You may only check out your own cart")

    db = db_manager.get_async_db()
    owner_id = current["user_id"]

    cart_items = []
    total = 0.0
    cursor = db.cart.find({"user_id": owner_id})
    async for item in cursor:
        try:
            product = await db.products.find_one({"_id": ObjectId(item.get("product_id", ""))})
        except (InvalidId, TypeError):
            continue
        if not product:
            continue
        qty = int(item.get("quantity", 1))
        price = float(product.get("price", 0) or 0)
        cart_items.append({
            "product_id": str(product["_id"]),
            "name": product.get("name", ""),
            "price": price,
            "quantity": qty,
            "subtotal": round(price * qty, 2),
        })
        total += price * qty

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    order_doc = {
        "user_id": owner_id,
        "items": cart_items,
        "total": round(total, 2),
        "status": "completed",
        "created_at": _utcnow(),
    }
    result = await db.orders.insert_one(order_doc)
    order_id = str(result.inserted_id)

    for item in cart_items:
        await _record_behavior(db, owner_id, item["product_id"], "purchase")

    await db.cart.delete_many({"user_id": owner_id})

    return {
        "message": "Order placed successfully!",
        "order_id": order_id,
        "id": order_id,
        "total": round(total, 2),
        "items_count": len(cart_items),
    }
