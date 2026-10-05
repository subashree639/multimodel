"""Order history endpoints (auth-protected, IDOR-safe)."""

from __future__ import annotations

import logging
from typing import Any, Dict

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user
from api.serializers import serialize_doc
from database.mongodb import db_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{user_id}")
async def get_orders(user_id: str, current: Dict[str, Any] = Depends(get_current_user)):
    """Get the authenticated user's order history."""
    if user_id not in (current["user_id"], "me", "current") and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="You may only read your own orders")

    db = db_manager.get_async_db()
    orders = []
    cursor = db.orders.find({"user_id": current["user_id"]}).sort("created_at", -1).limit(50)
    async for doc in cursor:
        orders.append(serialize_doc(doc))

    return {"user_id": current["user_id"], "orders": orders, "total_orders": len(orders)}


@router.get("/detail/{order_id}")
async def get_order_detail(order_id: str, current: Dict[str, Any] = Depends(get_current_user)):
    """Get a specific order; ownership is enforced unless the caller is admin."""
    try:
        oid = ObjectId(order_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Order not found")

    db = db_manager.get_async_db()
    doc = await db.orders.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found")

    if doc.get("user_id") != current["user_id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="You may only read your own orders")

    return serialize_doc(doc)
