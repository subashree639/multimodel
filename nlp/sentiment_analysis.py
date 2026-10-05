"""Sentiment analysis over product reviews.

Uses the ``cardiffnlp/twitter-roberta-base-sentiment-latest`` transformer
(3-class: positive / neutral / negative) through a transformers pipeline.
Every public method degrades to a neutral fallback instead of raising, so a
missing model can never take the API down.
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
NEUTRAL_FALLBACK = {"positive": 0.33, "negative": 0.33, "neutral": 0.34}

_instance: Optional["SentimentAnalyzer"] = None
_instance_lock = threading.Lock()


class SentimentAnalyzer:
    """Analyzes sentiment of product reviews using a pre-trained transformer."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.classifier = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the transformers pipeline; never raises."""
        try:
            from transformers import pipeline

            # Prefer the PyTorch backend: a TensorFlow/Keras 3 install makes
            # transformers raise at pipeline construction time.
            try:
                import torch  # noqa: F401

                framework = "pt"
            except Exception:
                framework = None

            kwargs = dict(
                task="sentiment-analysis",
                model=self.model_name,
                truncation=True,
                max_length=512,
            )
            if framework:
                kwargs["framework"] = framework

            self.classifier = pipeline(**kwargs)
            logger.info("Loaded sentiment model: %s (framework=%s)", self.model_name, framework)
        except Exception as e:
            logger.error("Failed to load sentiment model %s: %s", self.model_name, e)
            self.classifier = None

    @staticmethod
    def _to_scores(label: str, score: float) -> Dict[str, float]:
        """Convert a pipeline label/confidence into a 3-way probability dict."""
        label = (label or "").lower()
        pos = score if "positive" in label or label == "pos" else (1.0 - score) / 2.0
        neg = score if "negative" in label or label == "neg" else (1.0 - score) / 2.0
        neu = max(0.0, 1.0 - pos - neg)
        total = pos + neg + neu or 1.0
        return {
            "positive": round(pos / total, 4),
            "negative": round(neg / total, 4),
            "neutral": round(neu / total, 4),
        }

    def analyze(self, text: str) -> Dict[str, float]:
        """Return ``{positive, negative, neutral}`` for a single text."""
        if not self.classifier or not text or not text.strip():
            return dict(NEUTRAL_FALLBACK)
        try:
            results = self.classifier(text, truncation=True, max_length=512)
            if isinstance(results, list) and results and isinstance(results[0], list):
                results = results[0]
            return self._to_scores(results[0]["label"], float(results[0]["score"]))
        except Exception as e:
            logger.error("Sentiment analysis error: %s", e)
            return dict(NEUTRAL_FALLBACK)

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, float]]:
        """Analyze many texts with a single batched pipeline call.

        Falls back to per-item analysis if batched inference fails.
        """
        if not texts:
            return []
        if not self.classifier:
            return [dict(NEUTRAL_FALLBACK) for _ in texts]

        try:
            results = self.classifier(
                texts, truncation=True, max_length=512, batch_size=16
            )
            out: List[Dict[str, float]] = []
            for item in results:
                if isinstance(item, list):
                    item = item[0]
                out.append(self._to_scores(item["label"], float(item["score"])))
            return out
        except Exception as e:
            logger.warning("Batch sentiment failed, falling back to single calls: %s", e)
            return [self.analyze(t) for t in texts]

    def get_sentiment_label(self, scores: Dict[str, float]) -> str:
        """Return the dominant label for a score dict."""
        pos, neg, neu = scores.get("positive", 0.0), scores.get("negative", 0.0), scores.get("neutral", 0.0)
        if pos >= neg and pos >= neu:
            return "positive"
        if neg >= pos and neg >= neu:
            return "negative"
        return "neutral"

    def get_product_sentiment(self, reviews: List[Dict]) -> Dict:
        """Aggregate review documents into a product-level sentiment summary."""
        if not reviews:
            return {
                "avg_positive": 0.0,
                "avg_negative": 0.0,
                "avg_neutral": 0.0,
                "dominant_sentiment": "neutral",
                "total_reviews": 0,
            }
        scores = [
            r.get("sentiment_scores") or self.analyze(r.get("text", ""))
            for r in reviews
        ]
        avg_pos = float(np.mean([s.get("positive", 0.0) for s in scores]))
        avg_neg = float(np.mean([s.get("negative", 0.0) for s in scores]))
        avg_neu = float(np.mean([s.get("neutral", 0.0) for s in scores]))
        dominant = self.get_sentiment_label(
            {"positive": avg_pos, "negative": avg_neg, "neutral": avg_neu}
        )
        return {
            "avg_positive": round(avg_pos, 4),
            "avg_negative": round(avg_neg, 4),
            "avg_neutral": round(avg_neu, 4),
            "dominant_sentiment": dominant,
            "total_reviews": len(reviews),
        }


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Process-wide cached sentiment analyzer (model loaded at most once)."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = SentimentAnalyzer()
    return _instance
