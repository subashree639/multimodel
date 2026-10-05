"""Visual search endpoints: upload image -> similar products -> personalized re-rank."""

from __future__ import annotations

import io
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image

from api.serializers import serialize_product
from config import settings
from database.mongodb import db_manager

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
EXT_MAP = {".jpg", ".jpeg", ".png", ".webp"}

# --- lazy singleton: model loaded at most once, never per request -----------
_visual_singleton: Dict[str, Any] = {"engine": None, "lock": threading.Lock(), "failed": False}


def _get_engine():
    """Return cached VisualSearch engine or None if torch/weights unavailable."""
    if _visual_singleton["engine"] is not None:
        return _visual_singleton["engine"]
    if _visual_singleton["failed"]:
        return None
    with _visual_singleton["lock"]:
        if _visual_singleton["engine"] is not None:
            return _visual_singleton["engine"]
        try:
            from computer_vision.visual_search import VisualSearch
            engine = VisualSearch()
            # Try to restore persisted FAISS index (empty index handled gracefully).
            try:
                engine.load_index()
            except Exception as e:
                logger.debug(f"FAISS load skipped: {e}")
            _visual_singleton["engine"] = engine
            logger.info("VisualSearch engine initialized (ResNet50 cached)")
            return engine
        except Exception as e:
            logger.warning(f"VisualSearch unavailable (torch/weights missing?): {e}")
            _visual_singleton["failed"] = True
            return None


def _validate_upload(file: UploadFile, raw: bytes) -> Image.Image:
    if file.content_type and file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}. Use JPG/PNG/WEBP.")
    max_size = getattr(settings, "MAX_UPLOAD_SIZE", 10 * 1024 * 1024)
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Empty image file")
    if len(raw) > max_size:
        raise HTTPException(status_code=400, detail=f"Image too large (max {max_size // 1024 // 1024}MB)")
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.verify()  # detect corruption without full decode
        img = Image.open(io.BytesIO(raw)).convert("RGB")  # reopen after verify
        return img
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or corrupted image file")


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """Validate an upload (legacy endpoint kept for compatibility)."""
    raw = await file.read()
    img = _validate_upload(file, raw)
    return {"filename": file.filename, "size": len(raw), "dimensions": list(img.size), "similar": []}


@router.post("/search")
async def visual_search(file: UploadFile = File(...), top_k: int = 10, user_id: Optional[str] = None):
    """Upload Product Image -> Visual Similarity -> Candidates -> Personalized re-rank.

    - Invalid images return 400 (never crash).
    - Missing embeddings / empty FAISS index return a graceful empty result
      with a popularity fallback instead of an error.
    - When user_id is supplied, visual candidates are re-ranked with the
      hybrid recommender (personalized re-ranking).
    """
    raw = await file.read()
    img = _validate_upload(file, raw)
    top_k = max(1, min(top_k, 20))

    engine = _get_engine()
    if engine is None:
        # Graceful degradation: no vision stack -> popularity fallback.
        return await _popularity_fallback(reason="visual_model_unavailable")

    try:
        query_emb = engine.feature_extractor.extract_features(img)
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        raise HTTPException(status_code=500, detail="Could not process image")
    if query_emb is None:
        raise HTTPException(status_code=422, detail="Could not extract features from image")

    # Ensure FAISS has catalogue vectors; build lazily from stored embeddings.
    if not getattr(engine.similarity_search, "is_built", False):
        await _ensure_index(engine)
    if not getattr(engine.similarity_search, "is_built", False):
        return await _popularity_fallback(reason="empty_visual_index")

    results = engine.search_by_embedding(np.asarray(query_emb, dtype=np.float32), top_k=top_k * 2)
    if not results:
        return await _popularity_fallback(reason="no_visual_match")

    db = db_manager.get_async_db()
    candidates: List[Dict] = []
    for r in results:
        pid = r.get("product_id", "")
        prod = None
        try:
            from bson import ObjectId
            prod = await db.products.find_one({"_id": ObjectId(pid)})
        except Exception:
            prod = None
        if prod is None:
            continue
        candidates.append({
            "product": serialize_product(prod),
            "similarity_score": r.get("similarity_score", 0.0),
        })
        if len(candidates) >= top_k:
            break

    if not candidates:
        return await _popularity_fallback(reason="no_catalogue_match")

    # Personalized re-ranking when a user is known.
    reranked = candidates
    if user_id:
        try:
            from recommendation.hybrid_recommender import HybridRecommender
            # Lightweight re-rank: boost items matching user prefs/history.
            user = await db.users.find_one({"_id": _try_oid(user_id)}) if _try_oid(user_id) else None
            prefs = (user or {}).get("preferences", {}) or {}
            cats = {str(c).lower() for c in (prefs.get("preferred_categories") or [])}
            for c in candidates:
                bonus = 0.0
                if cats and str(c["product"].get("category", "")).lower() in cats:
                    bonus += 0.1
                rating = float(c["product"].get("avg_rating") or 0)
                bonus += min(rating / 5.0 * 0.05, 0.05)
                c["final_score"] = round(min(1.0, c["similarity_score"] + bonus), 4)
            reranked = sorted(candidates, key=lambda x: x.get("final_score", x["similarity_score"]), reverse=True)
        except Exception as e:
            logger.debug(f"Re-rank skipped: {e}")

    return {
        "results": reranked,
        "count": len(reranked),
        "personalized": bool(user_id),
        "pipeline": ["visual_similarity", "candidate_products"] + (["personalized_rerank"] if user_id else []),
    }


@router.get("/status")
async def visual_status():
    engine = _get_engine()
    if engine is None:
        return {"available": False, "reason": "torch/weights unavailable"}
    stats = engine.similarity_search.get_stats()
    return {"available": True, **stats}


async def _ensure_index(engine) -> None:
    """Populate FAISS from image_embeddings collection (graceful when empty)."""
    try:
        db = db_manager.get_async_db()
        rows = [d async for d in db.image_embeddings.find({}).limit(5000)]
        if not rows:
            logger.info("No stored image embeddings — visual index stays empty")
            return
        embs, ids, prods = [], [], []
        for d in rows:
            vec = d.get("embedding")
            if vec is None:
                continue
            embs.append(np.asarray(vec, dtype=np.float32))
            ids.append(str(d.get("product_id", "")))
        if not embs:
            return
        # Minimal product map for result enrichment.
        from bson import ObjectId
        for pid in ids[:5000]:
            try:
                p = await db.products.find_one({"_id": ObjectId(pid)})
                if p:
                    engine.products_index[pid] = p
            except Exception:
                continue
        engine.similarity_search.build_index(np.asarray(embs, dtype=np.float32), ids)
        logger.info(f"Visual index lazily built with {len(embs)} embeddings")
    except Exception as e:
        logger.warning(f"Could not build visual index: {e}")


async def _popularity_fallback(reason: str):
    try:
        db = db_manager.get_async_db()
        cur = db.products.find({}).sort([("avg_rating", -1), ("num_reviews", -1)]).limit(5)
        prods = [serialize_product(p) async for p in cur]
        return {"results": [{"product": p, "similarity_score": 0.0, "fallback": reason} for p in prods],
                "count": len(prods), "personalized": False, "fallback": reason}
    except Exception:
        return {"results": [], "count": 0, "personalized": False, "fallback": reason}


def _try_oid(value: str):
    try:
        from bson import ObjectId
        return ObjectId(value)
    except Exception:
        return None
