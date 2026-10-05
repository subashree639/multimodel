"""Shared FastAPI dependencies (authentication / authorization)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from database.mongodb import db_manager
from utils.security import JWTError, decode_access_token, is_token_expired

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


async def _load_user(user_id: str, email: str) -> Optional[Dict[str, Any]]:
    """Fetch a user document by id, falling back to email."""
    db = db_manager.get_async_db()
    try:
        from bson import ObjectId

        if len(str(user_id)) == 24:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                return user
    except Exception:
        pass
    if email:
        return await db.users.find_one({"email": email})
    return None


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Dict[str, Any]:
    """Validate the ``Authorization: Bearer <jwt>`` header and load the user.

    Raises 401 for missing/invalid/expired tokens and for unknown users.
    """
    if credentials is None or not credentials.credentials:
        raise _unauthorized("Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise _unauthorized("Invalid or expired token")
    if is_token_expired(payload):
        raise _unauthorized("Token has expired")

    user = await _load_user(payload.get("user_id", ""), payload.get("email", ""))
    if user is None:
        # Token is cryptographically valid but the account no longer exists.
        raise _unauthorized("User no longer exists")

    return {
        "user_id": str(user["_id"]),
        "email": user.get("email", payload.get("email", "")),
        "name": user.get("name", payload.get("name", "")),
        "role": user.get("role", "user"),
        "preferences": user.get("preferences", {}) or {},
        "document": user,
    }


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[Dict[str, Any]]:
    """Like :func:`get_current_user` but returns ``None`` instead of raising.

    Used by endpoints that support both anonymous visitors and logged-in users
    (e.g. recommendations).
    """
    if credentials is None or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


async def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency that rejects any user whose ``role`` is not ``admin``."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


def resolve_user_id(path_user_id: str, current: Optional[Dict[str, Any]]) -> str:
    """Reconcile a ``user_id`` path parameter with the authenticated user.

    Prevents IDOR: an authenticated caller may only act on its own id. The
    literal ``me`` is also accepted as an alias for the current user.
    """
    if path_user_id in ("me", "current"):
        if current is None:
            raise _unauthorized("Not authenticated")
        return current["user_id"]
    if current is not None and current["user_id"] != path_user_id:
        # Allow an admin to inspect other users' resources.
        if current.get("role") == "admin":
            return path_user_id
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only access your own resources",
        )
    if current is None:
        raise _unauthorized("Not authenticated")
    return path_user_id
