"""Build ResNet50 image embeddings for catalogue products.

Stores one vector per product in the ``image_embeddings`` collection, which
powers ``POST /api/v1/images/search`` (visual similarity + FAISS index).

Usage::

    python -m training.build_image_embeddings --limit 300
    python -m training.build_image_embeddings --limit 0 --force   # all products

Downloads product photos from their CDN, extracts 2048-d ResNet50 features
(L2 normalised) and upserts them. Failures (dead links, timeouts) are skipped
and reported — never fabricated.
"""

from __future__ import annotations

import argparse
import io
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

from config import settings
from database.mongodb import db_manager

logger = logging.getLogger("training.image_embeddings")

MODEL_NAME = "resnet50-imagenet1k-v1"
HEADERS = {"User-Agent": "MultiModalVisualSearch/1.0 (+product similarity)"}


def _download(url: str, timeout: float = 15.0) -> Optional[bytes]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
        if resp.status_code != 200:
            return None
        data = resp.content
        return data if data else None
    except Exception:
        return None


def _load_image(data: bytes):
    from PIL import Image

    img = Image.open(io.BytesIO(data))
    return img.convert("RGB")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=300,
                        help="number of products to process (0 = all)")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--force", action="store_true",
                        help="recompute even if an embedding already exists")
    parser.add_argument("--only-missing", action="store_true", default=True,
                        help="skip products that already have an embedding (default)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        stream=sys.stdout,
    )

    from computer_vision.feature_extractor import ResNet50FeatureExtractor

    t0 = time.time()
    db_manager.connect_sync()
    db = db_manager.get_sync_db()

    query: Dict = {"image_path": {"$regex": r"^https?://"}}
    if not args.force:
        query["_id"] = {"$nin": [
            row["product_id"] for row in db.image_embeddings.find({}, {"product_id": 1})
        ]}
    cursor = db.products.find(query, {"name": 1, "image_path": 1, "category": 1})
    if args.limit > 0:
        cursor = cursor.limit(args.limit)
    products = list(cursor)
    logger.info("Products to embed: %d", len(products))
    if not products:
        logger.info("Nothing to do — image_embeddings is already populated for this query")
        return 0

    logger.info("Loading %s ...", MODEL_NAME)
    extractor = ResNet50FeatureExtractor()

    # 1. parallel download
    urls = [p.get("image_path") for p in products]
    payloads: List[Optional[bytes]] = [None] * len(products)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_download, u): i for i, u in enumerate(urls) if u}
        done = 0
        for fut in as_completed(futures):
            i = futures[fut]
            payloads[i] = fut.result()
            done += 1
            if done % 50 == 0:
                logger.info("Downloaded %d/%d", done, len(futures))
    ok_downloads = sum(1 for p in payloads if p)
    logger.info("Downloaded %d/%d images in %.1fs",
                ok_downloads, len(products), time.time() - t0)

    # 2. batch feature extraction
    stored = skipped = failed = 0
    batch_imgs, batch_idx = [], []
    from pymongo import ReplaceOne

    def flush():
        nonlocal stored, failed, batch_imgs, batch_idx
        if not batch_imgs:
            return
        feats = extractor.extract_batch_features(batch_imgs)
        ops = []
        for feat, idx in zip(feats, batch_idx):
            if feat is None:
                failed += 1
                continue
            p = products[idx]
            ops.append(ReplaceOne(
                {"product_id": str(p["_id"])},
                {
                    "product_id": str(p["_id"]),
                    "embedding": [float(x) for x in feat.tolist()],
                    "image_path": p.get("image_path", ""),
                    "category": p.get("category", ""),
                    "model": MODEL_NAME,
                    "dim": int(feat.shape[0]),
                    "created_at": datetime.now(timezone.utc),
                },
                upsert=True,
            ))
        if ops:
            db.image_embeddings.bulk_write(ops, ordered=False)
            stored += len(ops)
        batch_imgs, batch_idx = [], []

    for i, data in enumerate(payloads):
        if data is None:
            skipped += 1
            continue
        try:
            batch_imgs.append(_load_image(data))
            batch_idx.append(i)
        except Exception:
            failed += 1
            continue
        if len(batch_imgs) >= args.batch_size:
            flush()
    flush()

    total = db.image_embeddings.count_documents({})
    logger.info(
        "Done: stored=%d skipped(no image)=%d failed=%d | collection total=%d | %.1fs",
        stored, skipped, failed, total, time.time() - t0,
    )
    if total:
        logger.info("Visual search index available: POST /api/v1/images/search")
    db_manager.disconnect_sync()
    return 0 if stored or total else 1


if __name__ == "__main__":
    raise SystemExit(main())
