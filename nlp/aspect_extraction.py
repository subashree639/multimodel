"""Aspect-based review analysis.

Splits review text into sentences, detects product aspects (battery, quality,
price, design, performance, size, delivery, ...) and — when a sentiment
function is supplied — scores each aspect from the sentences that mention it.

A lexicon is used for detection so the module works offline and costs nothing
at query time; the sentiment function may be a transformer-backed scorer.
"""

from __future__ import annotations

import logging
import re
from typing import Callable, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

SentimentFn = Callable[[str], Dict[str, float]]

#: Aspect name -> trigger phrases (lower-case, matched as substrings/word-ish).
ASPECT_LEXICON: Dict[str, List[str]] = {
    "battery": ["battery", "batteries", "charging", "charger", "charge life", "mah"],
    "quality": ["quality", "build", "durable", "durability", "flimsy", "sturdy", "material", "cheaply made", "well made"],
    "price": ["price", "pricing", "value", "expensive", "cheap", "cheaply priced", "worth", "affordable", "overpriced", "budget", "cost"],
    "design": ["design", "looks", "look", "style", "colour", "color", "sleek", "aesthetic", "finish"],
    "performance": ["performance", "fast", "speed", "slow", "powerful", "lag", "processor", "responsive", "snappy"],
    "size": ["size", "sizing", "small", "large", "big", "compact", "fits", "fit", "weight", "lightweight", "heavy"],
    "delivery": ["delivery", "shipping", "arrived", "packaging", "package", "dispatch", "delivered", "courier"],
    "service": ["customer service", "support", "warranty", "return", "refund", "replacement", "seller"],
    "ease_of_use": ["easy to use", "easy", "simple", "intuitive", "user friendly", "user-friendly", "setup", "instal", "install"],
    "screen": ["screen", "display", "resolution", "bright", "brightness", "panel"],
    "sound": ["sound", "audio", "speakers", "speaker", "bass", "noise", "volume"],
    "camera": ["camera", "photos", "photo", "picture", "pictures", "video", "lens", "megapixel"],
    "comfort": ["comfortable", "comfort", "cushion", "ergonomic", "grip", "soft"],
    "durability": ["lasted", "broke", "breaking", "scratch", "scratches", "rust", "wear"],
}

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def split_sentences(text: str) -> List[str]:
    """Split free text into sentences (lightweight, regex based)."""
    if not text or not text.strip():
        return []
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s and s.strip()]


def detect_aspects(text: str) -> List[str]:
    """Return the aspect names mentioned in ``text`` (order of lexicon)."""
    if not text:
        return []
    lowered = text.lower()
    found: List[str] = []
    for aspect, phrases in ASPECT_LEXICON.items():
        if any(phrase in lowered for phrase in phrases):
            found.append(aspect)
    return found


def extract_aspect_sentiments(
    text: str,
    sentiment_fn: Optional[SentimentFn] = None,
    max_sentences_per_aspect: int = 2,
) -> Dict[str, Dict[str, float]]:
    """Score each detected aspect from the sentences that mention it.

    Args:
        text: Review text.
        sentiment_fn: Callable returning ``{positive, negative, neutral}``.
            When ``None`` no per-aspect scores are produced (detection only).
        max_sentences_per_aspect: Cap on sentences scored per aspect so a long
            review cannot blow up inference cost.

    Returns:
        ``{aspect: {positive, negative, neutral, mentions}}``.
    """
    aspects = detect_aspects(text)
    if not aspects:
        return {}

    sentences = split_sentences(text)
    result: Dict[str, Dict[str, float]] = {}

    for aspect in aspects:
        triggers = ASPECT_LEXICON[aspect]
        matching = [
            s for s in sentences if any(t in s.lower() for t in triggers)
        ][:max_sentences_per_aspect]

        if sentiment_fn is None or not matching:
            # Detection only: report the aspect with neutral 1.0 so callers can
            # still see *that* the aspect was mentioned without inventing scores.
            result[aspect] = {
                "positive": 0.0,
                "negative": 0.0,
                "neutral": 1.0,
                "mentions": len(matching),
            }
            continue

        scores = [sentiment_fn(s) for s in matching]
        n = len(scores)
        result[aspect] = {
            "positive": round(sum(s.get("positive", 0.0) for s in scores) / n, 4),
            "negative": round(sum(s.get("negative", 0.0) for s in scores) / n, 4),
            "neutral": round(sum(s.get("neutral", 0.0) for s in scores) / n, 4),
            "mentions": n,
        }

    return result


def dominant_sentiment(scores: Dict[str, float]) -> str:
    """Return the dominant label of a ``{positive, negative, neutral}`` dict."""
    pos = scores.get("positive", 0.0)
    neg = scores.get("negative", 0.0)
    neu = scores.get("neutral", 0.0)
    if pos >= neg and pos >= neu:
        return "positive"
    if neg >= pos and neg >= neu:
        return "negative"
    return "neutral"


def aggregate_aspect_profile(reviews: Iterable[Dict]) -> Dict[str, Dict]:
    """Aggregate per-review ``aspect_sentiments`` into a product-level profile.

    Each review document is expected to carry ``aspect_sentiments`` as produced
    by :func:`extract_aspect_sentiments`. Returns::

        {aspect: {"count", "avg_positive", "avg_negative", "avg_neutral", "dominant"}}
    """
    buckets: Dict[str, List[Dict[str, float]]] = {}
    for review in reviews:
        for aspect, scores in (review.get("aspect_sentiments") or {}).items():
            buckets.setdefault(aspect, []).append(scores)

    profile: Dict[str, Dict] = {}
    for aspect, scores_list in buckets.items():
        n = len(scores_list)
        avg_pos = sum(s.get("positive", 0.0) for s in scores_list) / n
        avg_neg = sum(s.get("negative", 0.0) for s in scores_list) / n
        avg_neu = sum(s.get("neutral", 0.0) for s in scores_list) / n
        profile[aspect] = {
            "count": n,
            "avg_positive": round(avg_pos, 4),
            "avg_negative": round(avg_neg, 4),
            "avg_neutral": round(avg_neu, 4),
            "dominant": dominant_sentiment(
                {"positive": avg_pos, "negative": avg_neg, "neutral": avg_neu}
            ),
        }
    return profile
