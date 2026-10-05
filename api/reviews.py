"""Review endpoints: sentiment analysis, listing and submission."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_optional_user
from api.serializers import serialize_doc
from database.mongodb import db_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class ReviewRequest(BaseModel):
    product_id: str
    text: str = Field(..., min_length=1, max_length=5000)
    rating: int = Field(..., ge=1, le=5)


class ReviewSubmit(BaseModel):
    product_id: str
    text: str = Field(..., min_length=1, max_length=5000)
    rating: int = Field(..., ge=1, le=5)
    user_id: str = Field(
        default="guest",
        description="Ignored when an Authorization token is supplied.",
    )


def _rating_heuristic(rating: int) -> Dict[str, float]:
    if rating >= 4:
        return {"positive": 0.80, "negative": 0.05, "neutral": 0.15}
    if rating <= 2:
        return {"positive": 0.10, "negative": 0.75, "neutral": 0.15}
    return {"positive": 0.33, "negative": 0.33, "neutral": 0.34}


def _extract_keywords(text: str) -> list:
    try:
        from nlp.review_preprocessing import ReviewPreprocessor

        return ReviewPreprocessor().extract_keywords(text, top_k=5)
    except Exception as e:
        logger.debug("keyword extraction skipped: %s", e)
        return []


@router.post("/analyze")
def analyze_review(req: ReviewRequest):
    """Run sentiment analysis + aspect detection on review text."""
    from nlp.aspect_extraction import detect_aspects, extract_aspect_sentiments
    from nlp.sentiment_analysis import get_sentiment_analyzer

    analyzer = get_sentiment_analyzer()

    if analyzer.classifier is None:
        scores = _rating_heuristic(req.rating)
        label = max(scores, key=scores.get)
        return {
            "sentiment": label,
            "scores": scores,
            "keywords": [],
            "aspects": detect_aspects(req.text),
            "aspect_sentiments": {},
            "model_available": False,
        }

    scores = analyzer.analyze(req.text)
    label = analyzer.get_sentiment_label(scores)

    return {
        "sentiment": label,
        "scores": scores,
        "keywords": _extract_keywords(req.text),
        "aspects": detect_aspects(req.text),
        "aspect_sentiments": extract_aspect_sentiments(req.text, sentiment_fn=analyzer.analyze),
        "model_available": True,
    }


@router.get("/product/{product_id}")
async def get_reviews(product_id: str, limit: int = 50):
    """Fetch reviews for a product with aggregate sentiment and aspects."""
    db = db_manager.get_async_db()
    limit = max(1, min(limit, 100))

    try:
        total = await db.reviews.count_documents({"product_id": product_id})
        cursor = db.reviews.find({"product_id": product_id}).sort(
            "created_at", -1
        ).limit(limit)
        reviews = [serialize_doc(doc) async for doc in cursor]
    except Exception as e:
        logger.error("Error fetching reviews: %s", e)
        raise HTTPException(status_code=500, detail="Could not load reviews")

    if reviews:
        n = len(reviews)
        avg_pos = sum(r.get("sentiment_scores", {}).get("positive", 0) for r in reviews) / n
        avg_neg = sum(r.get("sentiment_scores", {}).get("negative", 0) for r in reviews) / n
        avg_neu = sum(r.get("sentiment_scores", {}).get("neutral", 0) for r in reviews) / n
        avg_rating = round(sum(r.get("rating", 0) for r in reviews) / n, 2)
    else:
        avg_pos = avg_neg = avg_neu = 0.0
        avg_rating = 0.0

    from nlp.aspect_extraction import aggregate_aspect_profile

    dominant = (
        "positive" if avg_pos >= avg_neg and avg_pos >= avg_neu
        else "negative" if avg_neg >= avg_pos and avg_neg >= avg_neu
        else "neutral"
    )
    if not reviews:
        dominant = "neutral"

    return {
        "product_id": product_id,
        "reviews": reviews,
        "total": total,
        "avg_rating": avg_rating,
        "sentiment_summary": {
            "positive": round(avg_pos, 4),
            "negative": round(avg_neg, 4),
            "neutral": round(avg_neu, 4),
            "dominant": dominant,
        },
        "aspect_profile": aggregate_aspect_profile(reviews),
    }


@router.post("/submit")
async def submit_review(
    req: ReviewSubmit,
    current: Optional[Dict[str, Any]] = Depends(get_optional_user),
):
    """Submit a review with transformer sentiment and aspect scoring.

    Anonymous submissions are stored under ``user_id='guest'``; authenticated
    submissions always use the token's user id (client-supplied ids are
    ignored, preventing spoofing).
    """
    db = db_manager.get_async_db()

    product = await db.products.find_one({"_id": ObjectId(req.product_id)}) if _is_valid(
        req.product_id
    ) else None
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    user_id = current["user_id"] if current else "guest"

    from nlp.aspect_extraction import extract_aspect_sentiments
    from nlp.sentiment_analysis import get_sentiment_analyzer

    analyzer = get_sentiment_analyzer()
    if analyzer.classifier is not None:
        scores = analyzer.analyze(req.text)
        label = analyzer.get_sentiment_label(scores)
        aspect_sentiments = extract_aspect_sentiments(req.text, sentiment_fn=analyzer.analyze)
    else:
        scores = _rating_heuristic(req.rating)
        label = max(scores, key=scores.get)
        aspect_sentiments = {}

    review_doc = {
        "product_id": req.product_id,
        "user_id": user_id,
        "rating": req.rating,
        "text": req.text,
        "sentiment": label,
        "sentiment_scores": scores,
        "aspect_sentiments": aspect_sentiments,
        "keywords": _extract_keywords(req.text),
        "created_at": datetime.now(timezone.utc),
    }

    from pymongo.errors import DuplicateKeyError

    try:
        result = await db.reviews.insert_one(review_doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409, detail="You have already reviewed this product"
        )
    except Exception as e:
        logger.error("Error submitting review: %s", e)
        raise HTTPException(status_code=500, detail="Failed to submit review")

    review_doc["id"] = str(result.inserted_id)
    review_doc.pop("_id", None)
    return {"message": "Review submitted", "review": review_doc}


def _is_valid(value: str) -> bool:
    try:
        ObjectId(value)
        return True
    except (InvalidId, TypeError):
        return False
