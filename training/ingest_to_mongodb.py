"""Seed MongoDB from the bundled CSV datasets.

Pipeline::

    datasets/sales/sales.csv              -> products
    datasets/customerbehaviour/*.csv      -> users (+ preferences/segments)
    training/synthetic_reviews.py         -> reviews (sentiment + aspects)
    review history                        -> orders (purchase signal)

Why reviews are generated instead of taken from ``datasets/reviews``: the two
source files share no join key (a Flipkart-style catalogue vs an Amazon review
corpus about a different product set), so raw reviews cannot be linked to
catalogue products coherently. See ``training/synthetic_reviews.py``.

Usage::

    python training/ingest_to_mongodb.py --products 1000 --active-users 150
    python training/ingest_to_mongodb.py --skip-sentiment   # faster, no model
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings
from database.mongodb import db_manager
from datasets.data_loader import DataLoader
from training.synthetic_reviews import generate_review_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEMO_EMAIL = "test@example.com"
SEED_USER_PASSWORD = os.getenv("SEED_USER_PASSWORD", "password123")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_product_docs(raw_products: Sequence[Dict]) -> List[Dict]:
    """Convert loader output into Mongo product documents."""
    now = _utcnow()
    docs = []
    for p in raw_products:
        name = str(p.get("name", "")).strip()
        category = str(p.get("category", "")).strip().lower()
        subcategory = str(p.get("subcategory", "")).strip().lower()
        price = float(p.get("price") or 0)

        # Word-level "features" derived from the product name give the TF-IDF
        # content model something richer than the bare title.
        tokens = [t for t in name.replace("/", " ").replace("-", " ").split() if len(t) > 3]
        features = list(dict.fromkeys(tokens))[:8]

        docs.append({
            "name": name,
            "category": category,
            "subcategory": subcategory,
            "price": price,
            "description": f"{name}. {subcategory.replace('_', ' ')} in {category}.",
            "features": features,
            "image_path": str(p.get("image_link", "")),
            "product_link": str(p.get("product_link", "")),
            "avg_rating": float(p.get("ratings") or 0),
            "num_reviews": int(p.get("no_of_ratings") or 0),
            "is_trending": False,
            "created_at": now,
            "updated_at": now,
        })
    return docs


def _preferred_categories(product_docs: Sequence[Dict], rng: random.Random) -> List[str]:
    """Pick 1-2 catalogue categories for a synthetic user profile."""
    categories = sorted({p["category"] for p in product_docs if p.get("category")})
    if not categories:
        return []
    return rng.sample(categories, k=min(2, len(categories)))


def build_user_docs(
    profiles: Sequence[Dict],
    product_docs: Sequence[Dict],
    hashed_password: str,
) -> List[Dict]:
    """Convert customer behaviour rows into Mongo user documents.

    ``preferences`` carries both display data and the numeric fields that
    ``nlp.customer_segmentation.CustomerSegmenter`` consumes, plus
    ``preferred_categories`` used by the content-based recommender for
    cold-start personalisation.
    """
    now = _utcnow()
    docs = []
    for u in profiles:
        seed = int(str(u.get("customer_id") or 0) or 0)
        local_rng = random.Random(seed)
        docs.append({
            "email": f"user{u['customer_id']}@example.com",
            "name": f"Customer {u['customer_id']}",
            "hashed_password": hashed_password,
            "role": "user",
            "preferences": {
                "city": u.get("city", ""),
                "membership": u.get("membership_type", ""),
                "gender": u.get("gender", ""),
                "age": int(u.get("age") or 0),
                "total_spend": float(u.get("total_spend") or 0),
                "items_purchased": int(u.get("items_purchased") or 0),
                "average_rating": float(u.get("average_rating") or 0),
                "days_since_last_purchase": int(u.get("days_since_last_purchase") or 0),
                "satisfaction_level": u.get("satisfaction_level", ""),
                "preferred_categories": _preferred_categories(product_docs, local_rng),
            },
            "created_at": now,
            "updated_at": now,
        })
    return docs


_SATISFACTION_BIAS = {"satisfied": 0.6, "neutral": 0.0, "unsatisfied": -0.9}


def _sample_rating(product: Dict, satisfaction: str, rng: random.Random) -> int:
    """Sample a rating around the product's real catalogue rating."""
    base = float(product.get("avg_rating") or 3.5)
    if base <= 0:
        base = 3.5
    bias = _SATISFACTION_BIAS.get(str(satisfaction).lower(), 0.0)
    # Blend the catalogue rating toward the mid-point so 5-star catalogues do
    # not saturate, then add the reviewer's disposition and noise.
    value = rng.gauss(base * 0.7 + 3.5 * 0.3 + bias, 0.7)
    return int(min(5, max(1, round(value))))


def build_reviews(
    active_users: Sequence[Dict],
    product_docs: Sequence[Dict],
    reviews_per_user: int,
    rng: random.Random,
) -> List[Dict]:
    """Create a user x product interaction graph.

    Each active user reviews ``reviews_per_user`` (+/- 2) products, mostly from
    their preferred categories. This yields the collaborative signal the SVD
    model needs while remaining a documented synthetic linkage.
    """
    if not product_docs or not active_users:
        return []

    by_category: Dict[str, List[int]] = {}
    for i, p in enumerate(product_docs):
        by_category.setdefault(p.get("category", ""), []).append(i)

    all_indexes = list(range(len(product_docs)))
    reviews: List[Dict] = []
    seen = set()

    for user in active_users:
        prefs = (user.get("preferences") or {}).get("preferred_categories") or []
        n = max(1, int(rng.gauss(reviews_per_user, 1.5)))
        for _ in range(n):
            if prefs and rng.random() < 0.8:
                cat = rng.choice(prefs)
                pool = by_category.get(cat) or all_indexes
            else:
                pool = all_indexes
            p_index = rng.choice(pool)
            key = (user["email"], p_index)
            if key in seen:
                continue
            seen.add(key)

            product = product_docs[p_index]
            rating = _sample_rating(
                product,
                (user.get("preferences") or {}).get("satisfaction_level", ""),
                rng,
            )
            reviews.append({
                "product_id": str(product["_id"]),
                "user_id": str(user["_id"]),
                "rating": rating,
                "product_index": p_index,
                "reviewer_name": user.get("name", ""),
            })
    return reviews


def attach_review_text(
    reviews: List[Dict],
    product_docs: Sequence[Dict],
    rng: random.Random,
) -> List[Dict]:
    """Fill in generated text/metadata for each synthetic review."""
    for r in reviews:
        product = product_docs[r["product_index"]]
        r["text"] = generate_review_text(
            product, r["rating"], rng, r.get("reviewer_name", "")
        )
        r["title"] = f"Review of {product['name'][:60]}"
        r["created_at"] = _utcnow() - timedelta(days=int(rng.random() * 180))
        r.pop("product_index", None)
        r.pop("reviewer_name", None)
    return reviews


def enrich_with_sentiment(reviews: List[Dict]) -> None:
    """Run transformer sentiment + aspect scoring over the generated texts.

    All sentences that need scoring are collected first and scored in a single
    batched pipeline call, instead of one model call per sentence.
    """
    from nlp.sentiment_analysis import get_sentiment_analyzer
    from nlp.aspect_extraction import ASPECT_LEXICON, detect_aspects, split_sentences
    from nlp.review_preprocessing import ReviewPreprocessor

    analyzer = get_sentiment_analyzer()
    preprocessor = ReviewPreprocessor()

    logger.info("Scoring sentiment for %d reviews...", len(reviews))
    scores = analyzer.analyze_batch([r["text"] for r in reviews])

    # ---- collect aspect-bearing sentences for one big batched pass ---------
    pending: List[List[tuple]] = []  # per review: [(aspect, sentence), ...]
    flat_sentences: List[str] = []
    for review in reviews:
        aspects = detect_aspects(review["text"])
        sentences = split_sentences(review["text"])
        per_review = []
        for aspect in aspects:
            triggers = ASPECT_LEXICON.get(aspect, [])
            matching = [
                s for s in sentences if any(t in s.lower() for t in triggers)
            ][:2]
            if matching:
                per_review.append((aspect, matching))
                flat_sentences.extend(matching)
        pending.append(per_review)

    aspect_scores = analyzer.analyze_batch(flat_sentences) if flat_sentences else []
    cursor = 0
    for review, score, per_review in zip(reviews, scores, pending):
        review["sentiment_scores"] = score
        review["sentiment"] = analyzer.get_sentiment_label(score)
        aspect_sentiments: Dict[str, Dict] = {}
        for aspect, matching in per_review:
            chunk = aspect_scores[cursor:cursor + len(matching)]
            cursor += len(matching)
            n = len(chunk) or 1
            aspect_sentiments[aspect] = {
                "positive": round(sum(s["positive"] for s in chunk) / n, 4),
                "negative": round(sum(s["negative"] for s in chunk) / n, 4),
                "neutral": round(sum(s["neutral"] for s in chunk) / n, 4),
                "mentions": len(chunk),
            }
        review["aspect_sentiments"] = aspect_sentiments
        try:
            review["keywords"] = preprocessor.extract_keywords(review["text"], top_k=5)
        except Exception:
            review["keywords"] = []


def _apply_neutral_defaults(reviews: List[Dict]) -> None:
    for r in reviews:
        r.setdefault("sentiment", "neutral")
        r.setdefault(
            "sentiment_scores",
            {"positive": 0.33, "negative": 0.33, "neutral": 0.34},
        )
        r.setdefault("aspect_sentiments", {})
        r.setdefault("keywords", [])


def build_orders_from_reviews(
    reviews: List[Dict],
    pid_to_product: Dict[str, Dict],
    rng: random.Random,
) -> List[Dict]:
    """Group a user's reviewed products into 1-3 purchase orders."""
    by_user: Dict[str, List[Dict]] = {}
    for r in reviews:
        by_user.setdefault(r["user_id"], []).append(r)

    orders: List[Dict] = []
    for user_id, user_reviews in by_user.items():
        items = list(user_reviews)
        rng.shuffle(items)
        pos = 0
        order_no = 0
        while pos < len(items) and order_no < 3:
            size = rng.randint(1, min(3, len(items) - pos))
            chunk = items[pos:pos + size]
            pos += size
            order_no += 1
            order_items = []
            for r in chunk:
                product = pid_to_product.get(r["product_id"])
                if not product:
                    continue
                price = float(product.get("price") or 0)
                qty = rng.choice([1, 1, 2])
                order_items.append({
                    "product_id": r["product_id"],
                    "name": product.get("name", ""),
                    "price": price,
                    "quantity": qty,
                    "subtotal": round(price * qty, 2),
                })
            if not order_items:
                continue
            orders.append({
                "user_id": user_id,
                "items": order_items,
                "total": round(sum(i["subtotal"] for i in order_items), 2),
                "status": "completed",
                "created_at": _utcnow() - timedelta(days=int(rng.random() * 150)),
            })
    return orders


async def ingest_data(args: argparse.Namespace) -> None:
    """Run the full ingestion pipeline."""
    await db_manager.connect_async()
    if not db_manager.is_connected:
        raise SystemExit("Could not connect to MongoDB — check MONGODB_URL in .env")
    db = db_manager.get_async_db()
    rng = random.Random(args.seed)

    loader = DataLoader(
        datasets_dir="datasets",
        max_products=args.products,
        max_reviews=0,
        max_customers=args.customers,
    )

    # ---------------------------------------------------------------- products
    logger.info("Loading product catalogue...")
    product_docs = build_product_docs(loader.get_product_catalog())
    if not product_docs:
        raise SystemExit("No products loaded — check datasets/sales/sales.csv")

    if not args.keep:
        for coll in ("products", "users", "reviews", "orders", "cart", "wishlist"):
            await db[coll].drop()

    result = await db.products.insert_many(product_docs, ordered=False)
    for doc, _id in zip(product_docs, result.inserted_ids):
        doc["_id"] = _id
    logger.info("Inserted %d products", len(product_docs))

    # ------------------------------------------------------------------- users
    logger.info("Loading customer profiles...")
    profiles = loader.get_customer_profiles()
    from utils.security import hash_password

    seed_hash = hash_password(SEED_USER_PASSWORD)
    user_docs = build_user_docs(profiles, product_docs, seed_hash)

    user_docs.append({
        "email": DEMO_EMAIL,
        "name": "Test User",
        "hashed_password": hash_password(SEED_USER_PASSWORD),
        "role": "user",
        "preferences": {
            "city": "Bengaluru",
            "membership": "Gold",
            "age": 29,
            "total_spend": 25000.0,
            "items_purchased": 18,
            "days_since_last_purchase": 12,
            "satisfaction_level": "Satisfied",
            "preferred_categories": _preferred_categories(product_docs, rng),
        },
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
    })

    # Admin account: password comes from the environment (never hard-coded).
    if os.getenv("ADMIN_PASSWORD"):
        user_docs.append({
            "email": settings.ADMIN_EMAIL,
            "name": "Admin",
            "hashed_password": hash_password(os.environ["ADMIN_PASSWORD"]),
            "role": "admin",
            "preferences": {"preferred_categories": []},
            "created_at": _utcnow(),
            "updated_at": _utcnow(),
        })
    else:
        logger.warning(
            "ADMIN_PASSWORD not set — skipping admin account. "
            "Set it and re-run ingestion to enable admin endpoints."
        )

    await db.users.insert_many(user_docs, ordered=False)
    users = [u async for u in db.users.find({})]
    logger.info("Inserted %d users", len(users))

    # ----------------------------------------------------------------- reviews
    active_users = [u for u in users if u.get("role") != "admin"]
    active_users.sort(key=lambda u: u["email"])
    rng.shuffle(active_users)
    active_users = active_users[: args.active_users]

    logger.info("Generating synthetic review interactions...")
    reviews = build_reviews(
        active_users, product_docs, args.reviews_per_user, rng
    )
    reviews = attach_review_text(reviews, product_docs, rng)

    if reviews and not args.skip_sentiment:
        try:
            enrich_with_sentiment(reviews)
        except Exception as e:
            logger.warning("Sentiment enrichment failed (%s); using neutral labels", e)
            _apply_neutral_defaults(reviews)
    else:
        _apply_neutral_defaults(reviews)

    if reviews:
        await db.reviews.insert_many(reviews, ordered=False)
    logger.info("Inserted %d reviews", len(reviews))

    # ------------------------------------------------------------------ orders
    pid_to_product = {str(p["_id"]): p for p in product_docs}
    orders = build_orders_from_reviews(reviews, pid_to_product, rng)
    if orders:
        await db.orders.insert_many(orders, ordered=False)
    logger.info("Inserted %d orders", len(orders))

    # ------------------------------------------------- startup analytics jobs
    try:
        from training.sales_analytics import SalesAnalyzer

        analyzer = SalesAnalyzer()
        await asyncio.to_thread(analyzer.update_database_trends)
        logger.info("Sales trends updated")
    except Exception as e:
        logger.warning("Sales analytics skipped: %s", e)

    try:
        from nlp.customer_segmentation import CustomerSegmenter

        segmenter = CustomerSegmenter()
        await asyncio.to_thread(segmenter.update_database_segments)
        logger.info("Customer segments updated")
    except Exception as e:
        logger.warning("Customer segmentation skipped: %s", e)

    await db_manager.disconnect_async()
    logger.info(
        "Ingestion complete: %d products, %d users, %d reviews, %d orders",
        len(product_docs), len(users), len(reviews), len(orders),
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed MongoDB from bundled CSVs")
    parser.add_argument("--products", type=int, default=1000, help="Max products to load (0 = all)")
    parser.add_argument("--customers", type=int, default=1000, help="Max customer rows (0 = all)")
    parser.add_argument("--active-users", type=int, default=150, help="Users that receive review history")
    parser.add_argument("--reviews-per-user", type=int, default=5, help="Mean reviews per active user")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (deterministic output)")
    parser.add_argument("--skip-sentiment", action="store_true", help="Skip transformer sentiment scoring")
    parser.add_argument("--keep", action="store_true", help="Do not drop existing collections")
    return parser.parse_args(argv)


if __name__ == "__main__":
    asyncio.run(ingest_data(parse_args()))
