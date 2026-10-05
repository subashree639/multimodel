"""Authentication routes: register / login / current-user.

Credentials are persisted in MongoDB and hashed with PBKDF2 (see
:mod:`utils.security`). Tokens are HS256 JWTs validated on every protected
route by :func:`api.deps.get_current_user`.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from config import settings
from database.mongodb import db_manager
from api.deps import get_current_user
from utils.security import (
    create_access_token,
    hash_password,
    password_strength_issues,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LoginRequest(BaseModel):
    email: str = Field(..., examples=["test@example.com"])
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    email: str = Field(..., examples=["jane@example.com"])
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=120)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    message: str = ""


class UserOut(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "user"
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _issue_token(user_doc: Dict[str, Any]) -> str:
    return create_access_token(
        user_id=str(user_doc["_id"]),
        email=user_doc["email"],
        name=user_doc.get("name", ""),
        role=user_doc.get("role", "user"),
    )


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest) -> TokenResponse:
    """Create a new account and return a JWT."""
    email = req.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Invalid email address")

    issues = password_strength_issues(req.password)
    if issues:
        raise HTTPException(status_code=422, detail="; ".join(issues))

    db = db_manager.get_async_db()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    user_doc = {
        "email": email,
        "name": req.name.strip(),
        "hashed_password": hash_password(req.password),
        "role": "user",
        "preferences": {},
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
    }
    try:
        from pymongo.errors import DuplicateKeyError

        result = await db.users.insert_one(user_doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Email already registered")
    except Exception as e:
        logger.error("Registration failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not create account")

    user_doc["_id"] = result.inserted_id
    logger.info("Registered user %s", email)
    return TokenResponse(
        access_token=_issue_token(user_doc),
        message=f"Account created successfully! Welcome, {req.name.strip()}!",
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    """Verify credentials and return a JWT."""
    email = req.email.strip().lower()
    db = db_manager.get_async_db()
    user = await db.users.find_one({"email": email})
    if user is None or not user.get("hashed_password"):
        # Same error for unknown user and wrong password (no user enumeration).
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenResponse(
        access_token=_issue_token(user),
        message=f"Welcome back, {user.get('name', email)}!",
    )


@router.get("/me", response_model=UserOut)
async def current_user(user: Dict[str, Any] = Depends(get_current_user)) -> UserOut:
    """Return the profile of the authenticated user."""
    doc = user["document"]
    created = doc.get("created_at")
    return UserOut(
        user_id=user["user_id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        preferences=user["preferences"],
        created_at=created.isoformat() if hasattr(created, "isoformat") else created,
    )
