"""Shared Mongo document → API response serializers.

Centralises the ``_id`` → ``id`` rewrite and the placeholder-image fallback so
the same logic is not copy/pasted across a dozen handlers.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

PLACEHOLDER_IMAGE = "/images/placeholder.png"


def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return a copy of ``doc`` with ``_id`` exposed as ``id``."""
    if doc is None:
        return None
    out = dict(doc)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    return out


def serialize_product(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Serialize a product document, guaranteeing ``id`` and ``image_path``."""
    out = serialize_doc(doc)
    if out is None:
        return None
    if not out.get("image_path"):
        out["image_path"] = PLACEHOLDER_IMAGE
    return out


def serialize_product_list(docs) -> list:
    """Serialize an iterable of product documents."""
    return [serialize_product(d) for d in docs if d is not None]
