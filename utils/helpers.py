import logging
import re
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def paginate_query(query: Any, page: int, page_size: int) -> Tuple[Any, Dict[str, Any]]:
    """
    Apply pagination to a MongoDB cursor or list.

    For Motor cursors, ``count`` is no longer supported — use
    ``estimated_document_count()`` / ``count_documents({})`` upstream if you
    need a total. Here we return ``total=None`` for cursor inputs to keep the
    helper fully synchronous.

    Returns:
        Tuple of (paginated_results, pagination_metadata)
    """
    if hasattr(query, 'skip') and hasattr(query, 'limit'):
        total = None
        results = query.skip((page - 1) * page_size).limit(page_size)
    else:
        items = list(query)
        total = len(items)
        start = (page - 1) * page_size
        results = items[start:start + page_size]

    meta = {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }
    return results, meta


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input by removing potentially dangerous characters."""
    if not isinstance(text, str):
        return ""
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    # Null byte removal
    text = text.replace('\x00', '')
    return text.strip()[:max_length]


def build_explanation(
    content_score: float = 0.0,
    collaborative_score: float = 0.0,
    sentiment_score: float = 0.0,
    matched_features: Optional[List[str]] = None,
    product: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build standardized recommendation explanation."""
    matched_features = matched_features or []
    return {
        "content_match": round(content_score, 4),
        "collaborative_match": round(collaborative_score, 4),
        "sentiment_alignment": round(sentiment_score, 4),
        "matched_features": matched_features,
        "product_category": product.get("category") if product else None,
        "product_rating": product.get("avg_rating") if product else None,
    }
