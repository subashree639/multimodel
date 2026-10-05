"""Password hashing and JWT helpers.

PBKDF2-HMAC-SHA256 from the standard library is used for password hashing so
the application has no dependency on ``passlib``/``bcrypt`` (passlib 1.7.x is
unmaintained and breaks against bcrypt >= 4.1/5.0). Legacy ``$2a$``/``$2b$``
bcrypt hashes are still verified when ``passlib`` is available, so previously
seeded accounts keep working.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt

from config import settings

logger = logging.getLogger(__name__)

PBKDF2_ITERATIONS = 390_000
_ALGO = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 (salted, per-password)."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return f"{_ALGO}${PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def _verify_pbkdf2(password: str, hashed: str) -> bool:
    try:
        _, iterations, salt, digest = hashed.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        )
        return hmac.compare_digest(dk.hex(), digest)
    except (ValueError, TypeError):
        return False


def _verify_bcrypt_legacy(password: str, hashed: str) -> bool:
    """Verify a legacy bcrypt hash if passlib/bcrypt are importable."""
    try:
        from passlib.context import CryptContext

        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return bool(ctx.verify(password, hashed))
    except Exception as e:  # pragma: no cover - depends on local bcrypt version
        logger.warning("Legacy bcrypt verification unavailable: %s", e)
        return False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify ``plain_password`` against either PBKDF2 or legacy bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    if hashed_password.startswith(f"{_ALGO}$"):
        return _verify_pbkdf2(plain_password, hashed_password)
    if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
        return _verify_bcrypt_legacy(plain_password, hashed_password)
    return False


def password_strength_issues(password: str) -> list:
    """Return a list of human-readable password policy violations (empty = OK)."""
    issues = []
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    if not any(c.isalpha() for c in password):
        issues.append("Password must contain at least one letter")
    if not any(c.isdigit() for c in password):
        issues.append("Password must contain at least one digit")
    return issues


def create_access_token(
    *,
    user_id: str,
    email: str,
    name: str,
    role: str = "user",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT containing the identity claims used across the app."""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: Dict[str, Any] = {
        "sub": email,
        "email": email,
        "name": name,
        "user_id": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode/validate a JWT.

    Raises:
        JWTError: if the token is invalid, expired or wrongly signed.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def is_token_expired(payload: Dict[str, Any]) -> bool:
    """Return True when the ``exp`` claim is in the past (or missing)."""
    exp = payload.get("exp")
    if exp is None:
        return True
    try:
        return datetime.fromtimestamp(float(exp), tz=timezone.utc) < datetime.now(timezone.utc)
    except (TypeError, ValueError, OSError):
        return True


__all__ = [
    "hash_password",
    "verify_password",
    "password_strength_issues",
    "create_access_token",
    "decode_access_token",
    "is_token_expired",
    "JWTError",
]
