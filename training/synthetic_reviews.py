"""Deterministic, category-aware review text generation.

The bundled datasets have **no join key**: ``datasets/sales`` is a
Flipkart-style product catalogue while ``datasets/reviews`` is an Amazon
review corpus about a different set of products (batteries / Fire tablets).
Attaching those raw reviews to catalogue products would produce incoherent
data, so reviews for the seeded catalogue are generated here from templates
that are aware of the product's category and of the aspect vocabulary used by
:mod:`nlp.aspect_extraction`.

Generation is fully deterministic for a given seed, so re-running ingestion
produces the same corpus.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional

#: Category fragment (matched against ``category``/``subcategory``) -> aspects
#: that make sense for that kind of product.
CATEGORY_ASPECTS: Dict[str, List[str]] = {
    "mobile": ["battery", "camera", "performance", "screen", "design", "price", "delivery"],
    "laptop": ["battery", "performance", "screen", "design", "price", "delivery"],
    "entertainment": ["sound", "performance", "screen", "design", "price"],
    "camera": ["camera", "performance", "design", "price"],
    "appliances": ["quality", "performance", "size", "noise", "price", "delivery", "ease_of_use"],
    "kitchen": ["quality", "size", "performance", "ease_of_use", "price", "delivery"],
    "home": ["quality", "design", "size", "comfort", "price", "delivery"],
    "beauty": ["quality", "design", "price", "delivery"],
    "person care": ["quality", "design", "price", "delivery"],
    "makeup": ["quality", "design", "price", "delivery"],
    "fashion": ["size", "comfort", "design", "quality", "price", "delivery"],
    "shoes": ["comfort", "size", "quality", "design", "price"],
    "bags": ["size", "quality", "design", "price", "delivery"],
    "sports": ["quality", "comfort", "size", "price", "delivery"],
    "toys": ["quality", "size", "safety", "price", "delivery"],
    "car": ["quality", "performance", "design", "price", "delivery"],
    "grocery": ["quality", "price", "delivery"],
    "pet": ["quality", "price", "delivery"],
    "stores": ["quality", "price", "delivery"],
    "default": ["quality", "price", "design", "delivery", "size"],
}

# Aspect -> sentences per polarity. Aspect names must exist in
# nlp.aspect_extraction.ASPECT_LEXICON (except "noise"/"safety" which fall back
# to generic sentences).
ASPECT_SENTENCES: Dict[str, Dict[str, List[str]]] = {
    "battery": {
        "positive": [
            "Battery life easily lasts a full day of heavy use.",
            "The battery charges fast and holds charge well.",
        ],
        "neutral": [
            "Battery life is about average, nothing remarkable.",
            "Battery performance is what you would expect at this price.",
        ],
        "negative": [
            "Battery drains quickly and needs constant charging.",
            "The battery barely lasts a few hours.",
        ],
    },
    "camera": {
        "positive": ["Photos come out sharp even in low light.", "The camera captures detailed pictures."],
        "neutral": ["Camera quality is decent for everyday shots."],
        "negative": ["Photos look washed out and grainy."],
    },
    "performance": {
        "positive": ["Performance is smooth even with many apps open.", "It runs everything without any lag."],
        "neutral": ["Performance is acceptable for normal daily tasks."],
        "negative": ["It struggles and lags constantly under normal use."],
    },
    "screen": {
        "positive": ["The display is bright and colours look great.", "Screen quality is excellent for videos."],
        "neutral": ["The display is fine for regular use."],
        "negative": ["The screen looks dim and colours are washed out."],
    },
    "sound": {
        "positive": ["Sound is clear with punchy bass.", "Speakers get loud without distortion."],
        "neutral": ["Sound quality is average."],
        "negative": ["Sound is tinny and gets distorted at high volume."],
    },
    "quality": {
        "positive": ["Build quality feels solid and premium.", "Materials feel durable and well finished."],
        "neutral": ["Build quality is average for this price range."],
        "negative": ["Feels cheaply made and started wearing out quickly."],
    },
    "design": {
        "positive": ["Looks stylish and the finish is really nice.", "Design is sleek and lightweight."],
        "neutral": ["Looks okay, nothing special about the design."],
        "negative": ["The design looks dated and bulky."],
    },
    "size": {
        "positive": ["Size is perfect and it fits exactly where I wanted."],
        "neutral": ["Size is as described in the listing."],
        "negative": ["Much smaller than expected from the description."],
    },
    "comfort": {
        "positive": ["Very comfortable to wear or use for long periods."],
        "neutral": ["Comfort is acceptable for short use."],
        "negative": ["Uncomfortable and causes fatigue quickly."],
    },
    "ease_of_use": {
        "positive": ["Setup took minutes and it is very easy to use."],
        "neutral": ["It is straightforward once you get used to it."],
        "negative": ["Confusing to set up and the instructions are unclear."],
    },
    "price": {
        "positive": ["Great value for the price I paid.", "Worth every rupee for what you get."],
        "neutral": ["Pricing is fair compared with similar options."],
        "negative": ["Overpriced for what it offers."],
    },
    "delivery": {
        "positive": ["Delivery was quick and the packaging was intact."],
        "neutral": ["Delivery arrived within the expected window."],
        "negative": ["Delivery was late and the packaging was damaged."],
    },
    "service": {
        "positive": ["Customer service responded quickly and resolved the issue."],
        "neutral": ["Support took a while but eventually replied."],
        "negative": ["Customer service was unhelpful and never resolved my complaint."],
    },
    "noise": {
        "positive": ["Runs almost silently."],
        "neutral": ["Noise level is noticeable but tolerable."],
        "negative": ["It is far too loud and noisy during operation."],
    },
    "safety": {
        "positive": ["Feels safe for kids and the parts are sturdy."],
        "neutral": ["Nothing unsafe, though the packaging could be better."],
        "negative": ["A part broke immediately, which felt unsafe."],
    },
}

OPENERS: Dict[str, List[str]] = {
    "positive": [
        "I have been using this {product} for a few weeks now and I am impressed.",
        "Purchased this {product} recently and it has been a great buy.",
        "Really happy with this {product} overall.",
        "This {product} exceeded my expectations.",
    ],
    "neutral": [
        "Bought this {product} and have been using it for a while.",
        "Mixed feelings about this {product} after regular use.",
        "This {product} is okay but has both strengths and weaknesses.",
    ],
    "negative": [
        "I am disappointed with this {product}.",
        "Regret buying this {product} after a week of use.",
        "This {product} has been frustrating to use.",
    ],
}

CLOSERS: Dict[str, List[str]] = {
    "positive": [
        "Would recommend it to anyone looking for a reliable option.",
        "I would happily buy it again.",
        "Five stars from my side.",
    ],
    "neutral": [
        "It does the job, but I would not call it outstanding.",
        "Fine for basic needs, consider alternatives if you want more.",
        "Three stars, it is average.",
    ],
    "negative": [
        "I would not recommend this one.",
        "Saving my money next time.",
        "One star for the experience I had.",
    ],
}


def _aspects_for(product: Dict, rng: random.Random, count: int = 2) -> List[str]:
    """Pick category-relevant aspects for a product."""
    haystack = f"{product.get('category', '')} {product.get('subcategory', '')}".lower()
    aspects: List[str] = []
    for key, values in CATEGORY_ASPECTS.items():
        if key != "default" and key in haystack:
            aspects = list(values)
            break
    if not aspects:
        aspects = list(CATEGORY_ASPECTS["default"])
    # "noise"/"safety" only make sense occasionally
    aspects = [a for a in aspects if a in ASPECT_SENTENCES]
    rng.shuffle(aspects)
    return aspects[: max(1, count)]


def polarity_for_rating(rating: int) -> str:
    """Map a 1-5 star rating to a sentiment polarity."""
    if rating >= 4:
        return "positive"
    if rating == 3:
        return "neutral"
    return "negative"


def generate_review_text(
    product: Dict,
    rating: int,
    rng: random.Random,
    reviewer_name: str = "",
) -> str:
    """Generate one coherent review for ``product`` at the given ``rating``.

    Args:
        product: Product document (uses ``name``/``category``/``subcategory``).
        rating: 1-5 star rating, drives the sentiment polarity.
        rng: Seeded random generator (determinism).
        reviewer_name: Optional name woven into the opening sentence.

    Returns:
        A 2-3 sentence review string.
    """
    name = str(product.get("name", "this product")).strip() or "this product"
    polarity = polarity_for_rating(int(rating))
    aspects = _aspects_for(product, rng, count=rng.choice([1, 2]))

    opener = rng.choice(OPENERS[polarity]).format(product=name)
    if reviewer_name and rng.random() < 0.3:
        opener = f"{reviewer_name} here. {opener}"

    sentences = [opener]
    for aspect in aspects:
        pool = ASPECT_SENTENCES.get(aspect, {}).get(polarity)
        if pool:
            sentences.append(rng.choice(pool))

    # occasional comparison / repeat-purchase sentence for positives
    if polarity == "positive" and rng.random() < 0.25:
        sentences.append(rng.choice([
            f"I compared a few options before buying this {name} and this one won.",
            "I would consider buying it again for another room.",
        ]))

    sentences.append(rng.choice(CLOSERS[polarity]))
    return " ".join(sentences)
